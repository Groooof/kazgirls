from loguru import logger
from pydantic_core import PydanticCustomError

from utils.libs import parse_number


def _base_phone_validator(phone: str) -> str:
    if isinstance(phone, int):
        phone = str(phone)
    phone = phone.strip()

    if phone.startswith(" "):
        phone = "+" + phone[1:]
    elif not phone.startswith("+"):
        phone = "+" + phone
    if not 10 < len(phone) < 15:
        raise PydanticCustomError("value_error", "Phone number length must be between 10 and 15")
    return phone


def _parse(phone: str, mobile: bool = True) -> str:
    try:
        return parse_number(phone, mobile=mobile)
    except ValueError as e:
        logger.critical("Invalid phone number format: {}", e.__repr__())
        raise PydanticCustomError("value_error", "Invalid phone number format. Use +7XXXXXXXXXX") from e


def mobile_phone_validator(phone: str) -> str:
    phone = _base_phone_validator(phone)
    return _parse(phone)


def phone_validator(phone: str) -> str:
    phone = _base_phone_validator(phone)
    return _parse(phone, mobile=False)
