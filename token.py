"""
File to return user their token
"""
from calendar import timegm
from datetime import datetime

from rest_framework_jwt.settings import api_settings


def get_token(user):
    """
    Return jwt token to user when aauthenticated
    :param user: user instance
    :type user: class MainUser
    :return: jwt token
    :rtype: str
    """
    jwt_payload_handler = api_settings.JWT_PAYLOAD_HANDLER
    jwt_encode_handler = api_settings.JWT_ENCODE_HANDLER
    payload = jwt_payload_handler(user)
    token = jwt_encode_handler(payload)
    if api_settings.JWT_ALLOW_REFRESH:
        """
        TODO (Nurymzhan) These lines added for refresh token, without orig_iat field
        token can not be refreshed. This field stores information about time,
        when old token created. Can you check correctness of time (now())
        """
        payload['orig_iat'] = timegm(
            datetime.utcnow().utctimetuple()
        )
    return token
