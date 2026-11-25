"""Authenticated research integration. No trading or position mutations."""
import hashlib
import ipaddress
import json
import math
import re
from datetime import date, datetime, timedelta, timezone
from urllib.parse import urlsplit

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import String, Text, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Mapped, Session, mapped_column

from app.database import Base, get_db
from app import models
from app.integration_auth import require_artemis_api_key

router=APIRouter(prefix='/automation',dependencies=[Depends(require_artemis_api_key)])
CRYPTO={'BTC-USD','ETH-USD','SOL-USD','XRP-USD','BNB-USD','ADA-USD','DOGE-USD','LTC-USD','BCH-USD','AVAX-USD'}
US={'NMS','NGM','NCM','NYQ','ASE','PCX','BTS','NASDAQ','NYSE','NYSEARCA','NYSEAMERICAN','BATS'}

class ResearchRecord(Base):
    __tablename__='artemis_market_research'
    id: Mapped[str]=mapped_column(String(64),primary_key=True)
    asset_id: Mapped[int]=mapped_column(nullable=False,index=True)
    payload: Mapped[str]=mapped_column(Text,nullable=False)
    created_at: Mapped[str]=mapped_column(String(40),nullable=False,index=True)


def valid_symbol(value):
    value=value.strip().upper()
    if not re.fullmatch(r'[A-Z][A-Z0-9.-]{0,19}',value):raise ValueError('Invalid symbol.')
    return value


def identity(info,requested):
    symbol=valid_symbol(requested)
    if info.get('symbol','').upper()!=symbol:raise ValueError('Provider symbol mismatch.')
    kind={'EQUITY':'Equity','ETF':'ETF','CRYPTOCURRENCY':'Crypto'}.get(info.get('quoteType'))
    exchange=str(info.get('exchange','')).upper()
    if not kind or info.get('currency')!='USD':raise ValueError('Only USD US-listed stocks/ETFs and selected USD cryptocurrency pairs are supported.')
    if kind=='Crypto':
        if symbol not in CRYPTO:raise ValueError('Cryptocurrency is outside the configured major-pair universe.')
    elif exchange not in US:raise ValueError('Listing exchange is outside the US universe.')
    name=info.get('longName')or info.get('shortName')
    if not name:raise ValueError('Provider issuer/fund name missing.')
    return dict(symbol=symbol,name=name,asset_type=kind,exchange=exchange,currency='USD')


class Track(BaseModel):
    symbol:str=Field(min_length=1,max_length=20)


@router.get('/health')
def automation_health():
    return {'status':'healthy','access':'research-writes','capabilities':['resolve-assets','refresh-prices','append-research'],'trading':False}


@router.get('/discover')
def discover(q:str=Query(min_length=1,max_length=120)):
    import yfinance as yf
    try:
        quotes=yf.Search(q,max_results=8,news_count=0).quotes
        return [{'symbol':valid_symbol(x['symbol']),'name':x.get('longname')or x.get('shortname')or x['symbol']}for x in quotes if x.get('quoteType')in {'EQUITY','ETF','CRYPTOCURRENCY'} and re.fullmatch(r'[A-Z][A-Z0-9.-]{0,19}',x.get('symbol',''))][:8]
    except Exception as e:raise HTTPException(502,'Symbol provider lookup failed.')from e


@router.post('/track')
def track(body:Track,database:Session=Depends(get_db)):
    import yfinance as yf
    try:
        symbol=valid_symbol(body.symbol)
        fields=identity(yf.Ticker(symbol).get_info(),symbol)
    except ValueError as e:raise HTTPException(422,str(e))from e
    except Exception as e:raise HTTPException(502,'Listing metadata unavailable; no asset created.')from e
    asset=database.scalar(select(models.MarketAsset).where(models.MarketAsset.symbol==symbol))
    if asset:
        if not asset.is_active:raise HTTPException(409,'Asset is inactive; automatic tracking will not reactivate it.')
        if asset.asset_type!=fields['asset_type']or asset.currency!='USD' or (asset.exchange and str(asset.exchange).upper()not in (US if asset.asset_type!='Crypto'else {fields['exchange']})):
            raise HTTPException(409,'Existing asset metadata conflicts with provider scope. Resolve it in Market Lens.')
        # Existing identity is not silently overwritten or merged on name similarity.
        clean=lambda s:re.sub(r'[^a-z0-9]','',str(s).casefold())
        if asset.name and clean(asset.name)!=clean(fields['name']):raise HTTPException(409,'Existing asset name differs from current provider metadata; review identity before automation.')
    else:
        asset=models.MarketAsset(**fields,is_active=True);database.add(asset)
        try:database.commit();database.refresh(asset)
        except IntegrityError:
            database.rollback();raise HTTPException(409,'Concurrent asset creation; retry to resolve the stored asset.')
    return dict(id=asset.id,**fields,identity_status='provider_metadata_confirmed',provider='Yahoo Finance via yfinance',checked_at=datetime.now(timezone.utc).isoformat())


@router.post('/assets/{asset_id}/refresh')
def refresh(asset_id:int,database:Session=Depends(get_db)):
    from app.main import sync_asset_market_data
    asset=database.get(models.MarketAsset,asset_id)
    if not asset or not asset.is_active:raise HTTPException(404,'Active asset not found.')
    end=datetime.now(timezone.utc).date()-timedelta(days=1)
    return sync_asset_market_data(asset_id,end-timedelta(days=400),end,database)


def public_url(url):
    try:
        p=urlsplit(url);host=p.hostname
        if p.scheme!='https'or not host or '.'not in host or host.endswith(('.localhost','.local'))or p.username or p.password:return False
        try:return ipaddress.ip_address(host).is_global
        except ValueError:return host not in {'localhost','localhost.localdomain'}
    except ValueError:return False


class ResearchWrite(BaseModel):
    record:dict


def validate_record(record):
    if len(json.dumps(record))>100000:raise ValueError('Research record too large.')
    if record.get('direction')not in {'bullish','bearish','neutral','insufficient_evidence'}:raise ValueError('Invalid outlook direction.')
    asof=date.fromisoformat(record['as_of']);target=date.fromisoformat(record['horizon_end'])
    if not 1<=(target-asof).days<=90 or asof>datetime.now(timezone.utc).date():raise ValueError('Invalid forecast horizon.')
    created=datetime.fromisoformat(record['created_at'])
    if created.tzinfo is None or created.date()!=asof:raise ValueError('Invalid creation timestamp.')
    if not isinstance(record.get('reasoning'),str)or len(record['reasoning'])>2500:raise ValueError('Invalid research reasoning.')
    baseline=record.get('baseline',{})
    if baseline and (date.fromisoformat(baseline['trading_date'])>asof or not math.isfinite(float(baseline['close_price']))or float(baseline['close_price'])<=0):raise ValueError('Invalid price baseline.')
    evidence=record.get('evidence',[])
    if len(evidence)>12:raise ValueError('Too much evidence.')
    for e in evidence:
        if not public_url(e['url'])or not e.get('quote')or len(e['quote'])>4000:raise ValueError('Invalid evidence provenance.')
    if record['direction']!='insufficient_evidence' and (not baseline or not evidence or (asof-date.fromisoformat(baseline['trading_date'])).days>7):raise ValueError('Directional outlook requires a price baseline and dated source evidence.')
    for e in evidence:
        published=date.fromisoformat(e.get('published_at','')[:10])
        if not asof-timedelta(days=30)<=published<=asof:raise ValueError('Evidence is not recently dated at the forecast cutoff.')
    return record


@router.post('/assets/{asset_id}/research')
def save_research(asset_id:int,body:ResearchWrite,database:Session=Depends(get_db)):
    asset=database.get(models.MarketAsset,asset_id)
    if not asset:raise HTTPException(404,'Asset not found.')
    try:record=validate_record(body.record)
    except (ValueError,KeyError,TypeError)as e:raise HTTPException(422,'Research record failed validation.')from e
    if record.get('symbol')!=asset.symbol:raise HTTPException(422,'Research symbol mismatch.')
    key=hashlib.sha256(json.dumps([asset_id,record.get('research_key')or record],sort_keys=True).encode()).hexdigest()
    row=database.get(ResearchRecord,key)
    if row is None:
        database.add(ResearchRecord(id=key,asset_id=asset_id,payload=json.dumps(record,ensure_ascii=False),created_at=record['created_at']))
        try:database.commit()
        except IntegrityError:database.rollback()
        row=database.get(ResearchRecord,key)
    return {'id':key,'asset_id':asset_id,'saved':True,'direction':json.loads(row.payload)['direction']if row else record['direction']}


def outcome(record,bars,today):
    if record['direction']=='insufficient_evidence':return {'status':'not_assessed'}
    target=date.fromisoformat(record['horizon_end'])
    if today<target:return {'status':'pending','due':target.isoformat()}
    bars=[b for b in bars if b.trading_date<today]
    baseline_date=record.get('baseline',{}).get('trading_date')
    baseline=next((b for b in bars if b.trading_date.isoformat()==baseline_date),None)
    end=next((b for b in bars if target<=b.trading_date<=target+timedelta(days=7)),None)
    if not baseline or not end:return {'status':'price_data_missing'}
    adjusted=baseline.adjusted_close is not None and end.adjusted_close is not None
    start=float(baseline.adjusted_close if adjusted else baseline.close_price);finish=float(end.adjusted_close if adjusted else end.close_price)
    if start<=0:return {'status':'price_data_missing'}
    change=(finish/start-1)*100;actual='bullish'if change>1 else 'bearish'if change< -1 else 'neutral'
    return {'status':'evaluated','return_percent':round(change,4),'observed_direction':actual,'direction_matched':actual==record['direction'],'observation_date':end.trading_date.isoformat(),'basis':'latest stored adjusted-close series'if adjusted else 'unadjusted close; corporate actions can distort results','neutral_band_percent':1,'limits':'Calendar horizon; first available session within seven days. Price-series revisions may change this evaluation. Not a calibrated success rate or investment return.'}


@router.get('/research')
def research(limit:int=Query(default=100,ge=1,le=300),database:Session=Depends(get_db)):
    rows=database.scalars(select(ResearchRecord).order_by(ResearchRecord.created_at.desc()).limit(limit)).all()
    records=sorted([(r,json.loads(r.payload))for r in rows],key=lambda pair:pair[1].get('created_at',''),reverse=True)[:limit]
    output=[]
    for row,record in records:
        bars=database.scalars(select(models.PriceBar).where(models.PriceBar.asset_id==row.asset_id).order_by(models.PriceBar.trading_date)).all()
        output.append({'id':row.id,'asset_id':row.asset_id,'record':record,'outcome':outcome(record,bars,datetime.now(timezone.utc).date())})
    return output
