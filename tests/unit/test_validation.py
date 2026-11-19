import pytest
from pydantic import ValidationError

from app.core.errors import ValidationFailed
from app.core.idempotency import require_idempotency_key
from app.modules.admin.schemas import FundingRequest
from app.modules.auth.schemas import RegisterRequest
from app.modules.transfers.schemas import TransferRequest
from app.modules.users.schemas import UpdateProfileRequest


class TestRegister:
    def test_valid_input_is_normalised(self):
        req = RegisterRequest(name="  Asha   Rao ", email=" Asha@Example.COM ", password="pass1234")
        assert req.name == "Asha Rao"
        assert req.email == "asha@example.com"

    def test_client_cannot_choose_role(self):
        with pytest.raises(ValidationError):
            RegisterRequest(name="A", email="a@b.co", password="pass1234", role="admin")

    @pytest.mark.parametrize(
        "fields",
        [
            {"name": "", "email": "a@b.co", "password": "pass1234"},
            {"name": "A", "email": "not-an-email", "password": "pass1234"},
            {"name": "A", "email": "a@b.co", "password": "short"},
            {"name": "A", "email": "a@b.co", "password": "é" * 40},  # > 72 bytes
        ],
    )
    def test_invalid_input(self, fields):
        with pytest.raises(ValidationError):
            RegisterRequest(**fields)


class TestTransferRequest:
    def test_integer_paise_accepted_including_zero_and_negative(self):
        # zero/negative are recorded as failed attempts by the service, not rejected here
        for amount in (1, 0, -500):
            assert TransferRequest(
                recipient_user_id="usrabc", amount_paise=amount
            ).amount_paise == (amount)

    def test_recipient_is_normalised(self):
        assert TransferRequest(recipient_user_id=" usrabc ", amount_paise=1).recipient_user_id == (
            "USRABC"
        )

    @pytest.mark.parametrize("amount", [10.5, 100.0, "100", True, 2**63])
    def test_floats_strings_bools_and_overflow_rejected(self, amount):
        with pytest.raises(ValidationError):
            TransferRequest.model_validate_json(
                f'{{"recipient_user_id": "USRX", "amount_paise": {_json(amount)}}}'
            )

    def test_extra_fields_rejected(self):
        with pytest.raises(ValidationError):
            TransferRequest(recipient_user_id="U", amount_paise=1, sender_user_id="X")


def _json(value):
    import json

    return json.dumps(value)


def test_funding_request_is_strict_int():
    with pytest.raises(ValidationError):
        FundingRequest.model_validate_json('{"recipient_user_id": "USRX", "amount_paise": 1.0}')


def test_profile_update_allows_only_name():
    assert UpdateProfileRequest(name="New Name").name == "New Name"
    for field in ("email", "user_id", "role"):
        with pytest.raises(ValidationError):
            UpdateProfileRequest(name="N", **{field: "x"})


class TestIdempotencyKey:
    def test_valid(self):
        assert require_idempotency_key("abc-123_XYZ") == "abc-123_XYZ"

    @pytest.mark.parametrize("bad", [None, "", "   ", "short", "has space here", "x" * 129])
    def test_invalid(self, bad):
        with pytest.raises(ValidationFailed):
            require_idempotency_key(bad)
