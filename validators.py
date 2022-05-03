"""
Validators needed to auth_ app
"""
from apps.utils import messages
from apps.utils.string_utils import valid_phone
from django.core.exceptions import ValidationError


def phone_validator(phone):
    """
    Validator for phone number. Checks the phone that the number exists and correct mobile operator.
    :param phone: phone number of user
    :type phone: str
    :raises: :class:`ValidationError`: phone number is invalid
    """
    if not valid_phone(phone):
        raise ValidationError(messages.PHONE_INVALID)


def full_name_validator(value):
    """
    Validator which checks full name. Checks that full name doesn't contain other symbols
    besides letters.
    :param value: full name of user
    :type value: str
    :raises: :class:`ValidationError`: full name doesn't contain only letters
    """
    if not value.replace(' ', '').replace('-', '').isalpha():
        raise ValidationError(messages.INVALID_FULL_NAME)
