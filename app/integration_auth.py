import os
import secrets

from dotenv import load_dotenv
from fastapi import (
    Header,
    HTTPException,
    status,
)


load_dotenv()


ARTEMIS_API_KEY_ENVIRONMENT_VARIABLE = (
    "MARKET_LENS_ARTEMIS_API_KEY"
)

MINIMUM_API_KEY_LENGTH = 32


def get_configured_artemis_api_key() -> str:
    configured_key = os.getenv(
        ARTEMIS_API_KEY_ENVIRONMENT_VARIABLE,
        "",
    )

    if (
        not configured_key
        or len(configured_key)
        < MINIMUM_API_KEY_LENGTH
    ):
        raise HTTPException(
            status_code=(
                status.HTTP_503_SERVICE_UNAVAILABLE
            ),
            detail=(
                "The Artemis integration is not "
                "configured."
            ),
        )

    return configured_key


def require_artemis_api_key(
    x_artemis_key: str | None = Header(
        default=None,
        alias="X-Artemis-Key",
    ),
) -> None:
    configured_key = (
        get_configured_artemis_api_key()
    )

    if (
        x_artemis_key is None
        or not secrets.compare_digest(
            x_artemis_key,
            configured_key,
        )
    ):
        raise HTTPException(
            status_code=(
                status.HTTP_401_UNAUTHORIZED
            ),
            detail=(
                "A valid Artemis integration "
                "API key is required."
            ),
            headers={
                "WWW-Authenticate": (
                    "ArtemisApiKey"
                ),
            },
        )