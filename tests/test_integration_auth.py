import pytest
from fastapi import HTTPException

from app.integration_auth import (
    ARTEMIS_API_KEY_ENVIRONMENT_VARIABLE,
    get_configured_artemis_api_key,
    require_artemis_api_key,
)


TEST_API_KEY = (
    "market-lens-artemis-test-key-"
    "0123456789abcdef"
)


@pytest.fixture(autouse=True)
def clear_integration_api_key(
    monkeypatch,
):
    monkeypatch.delenv(
        ARTEMIS_API_KEY_ENVIRONMENT_VARIABLE,
        raising=False,
    )


def test_missing_configuration_is_unavailable():
    with pytest.raises(
        HTTPException
    ) as error_info:
        get_configured_artemis_api_key()

    assert (
        error_info.value.status_code
        == 503
    )

    assert (
        error_info.value.detail
        == (
            "The Artemis integration is not "
            "configured."
        )
    )


def test_short_configuration_is_unavailable(
    monkeypatch,
):
    monkeypatch.setenv(
        ARTEMIS_API_KEY_ENVIRONMENT_VARIABLE,
        "too-short",
    )

    with pytest.raises(
        HTTPException
    ) as error_info:
        get_configured_artemis_api_key()

    assert (
        error_info.value.status_code
        == 503
    )


def test_configured_key_is_returned(
    monkeypatch,
):
    monkeypatch.setenv(
        ARTEMIS_API_KEY_ENVIRONMENT_VARIABLE,
        TEST_API_KEY,
    )

    assert (
        get_configured_artemis_api_key()
        == TEST_API_KEY
    )


def test_missing_request_key_is_rejected(
    monkeypatch,
):
    monkeypatch.setenv(
        ARTEMIS_API_KEY_ENVIRONMENT_VARIABLE,
        TEST_API_KEY,
    )

    with pytest.raises(
        HTTPException
    ) as error_info:
        require_artemis_api_key(None)

    assert (
        error_info.value.status_code
        == 401
    )


def test_incorrect_request_key_is_rejected(
    monkeypatch,
):
    monkeypatch.setenv(
        ARTEMIS_API_KEY_ENVIRONMENT_VARIABLE,
        TEST_API_KEY,
    )

    with pytest.raises(
        HTTPException
    ) as error_info:
        require_artemis_api_key(
            "incorrect-key"
        )

    assert (
        error_info.value.status_code
        == 401
    )

    assert (
        error_info.value.headers
        == {
            "WWW-Authenticate": (
                "ArtemisApiKey"
            ),
        }
    )


def test_correct_request_key_is_accepted(
    monkeypatch,
):
    monkeypatch.setenv(
        ARTEMIS_API_KEY_ENVIRONMENT_VARIABLE,
        TEST_API_KEY,
    )

    assert (
        require_artemis_api_key(
            TEST_API_KEY
        )
        is None
    )