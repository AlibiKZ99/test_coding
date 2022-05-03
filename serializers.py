"""
This file represents rules for returning data from a database and getting data.
"""
from calendar import timegm
from datetime import timedelta, datetime
from django.contrib.auth import get_user_model
from apps.auth_.models import Activation, MainUser
from apps.auth_.validators import phone_validator
from apps.utils.exceptions import CommonException
from apps.utils import codes, messages
from rest_framework_jwt.settings import api_settings
from rest_framework_jwt.utils import jwt_get_secret_key
from rest_framework_jwt.serializers import VerificationBaseSerializer, \
    jwt_payload_handler, jwt_encode_handler
import jwt
import uuid
import logging

from rest_framework import serializers

User = get_user_model()

logger = logging.getLogger(__name__)


class ActivationSerializer(serializers.ModelSerializer):
    """
    Activation model serializer.
    Return id and pgone or accept phone
    """

    class Meta:
        model = Activation
        fields = ('id', 'phone')


class ActivationCodeSerializer(serializers.Serializer):
    """
    Serializer to accept code for activating account
    """
    code = serializers.CharField(max_length=4)


class PhoneSerializer(serializers.Serializer):
    """
    Serializer to accept phone of user
    """
    phone = serializers.CharField(max_length=30, validators=[phone_validator])


class RegistrationSerializer(serializers.ModelSerializer):
    """
    Registration serializer, takes full_name and email of the user, then returns these fields.
    """
    class Meta:
        model = MainUser
        fields = ('full_name', 'email')

    def complete_registration(self, instance):
        """
        Function which set the entered data to created user instance
        :param instance: created user
        :type instance: class MainUser
        """
        instance.full_name = self.validated_data['full_name']
        instance.email = self.validated_data['email']
        instance.is_registered = True
        instance.save()


class UserSerializer(serializers.ModelSerializer):
    """
    User model serializer.
    """
    class Meta:
        model = User
        fields = ('id', 'username', 'phone', 'email',
                  'full_name', 'is_registered', 'birth_date', 'avatar_url')


class UserProfileSerializer(serializers.Serializer):
    """
    User's profile seralizer to change avatar and full name of the user.
    """
    avatar_url = serializers.CharField(max_length=555, required=False)
    full_name = serializers.CharField(max_length=555, required=False)

    def update(self, instance, validated_data):
        """
        Function update full name and avatar of the existing user.
        :param instance: existing user
        :type instance: class MainUser
        :param validated_data: fields which is need to change (avatar_url and full_name)
        :type validated_data: json
        :return: changed user instance
        :rtype: class MainUser
        """
        instance.full_name = validated_data.get('full_name', instance.full_name)
        instance.avatar_url = validated_data.get('avatar_url', instance.avatar_url)
        instance.save()
        return instance

    class Meta:
        model = User
        fields = ('avatar_url', 'full_name')


class CustomRefreshJSONWebTokenSerializer(VerificationBaseSerializer):
    """
    Refresh an access token.
    """

    def jwt_decode_handler(self, token):
        try:
            options = {
                'verify_exp': False,
            }
            # get user from token, BEFORE verification, to get user secret key
            unverified_payload = jwt.decode(token, None, False)
            secret_key = jwt_get_secret_key(unverified_payload)
            return jwt.decode(
                token,
                api_settings.JWT_PUBLIC_KEY or secret_key,
                api_settings.JWT_VERIFY,
                options=options,
                leeway=api_settings.JWT_LEEWAY,
                audience=api_settings.JWT_AUDIENCE,
                issuer=api_settings.JWT_ISSUER,
                algorithms=[api_settings.JWT_ALGORITHM]
            )
        except jwt.InvalidSignatureError as e:
            logger.error(e)
            raise CommonException(code=codes.TOKEN_EXPIRED, detail=str(e))
        except Exception as e:
            logger.error(e)
            raise CommonException(status_code=codes.UNAUTHORIZED,
                                  code=codes.UNAUTHORIZED, detail=str(e))

    def _check_payload(self, token):
        # Check payload valid (based off of JSONWebTokenAuthentication,
        # may want to refactor)
        try:
            payload = self.jwt_decode_handler(token)
        except jwt.ExpiredSignature:
            raise CommonException(code=codes.TOKEN_REFRESH_EXPIRED,
                                  detail=messages.SIGNATURE_HAS_EXPIRED)
        except jwt.DecodeError:
            raise CommonException(code=codes.TOKEN_REFRESH_EXPIRED,
                                  detail=messages.ERROR_DECODING_SIGNATURE)

        return payload

    def validate(self, attrs):
        token = attrs['token']

        payload = self._check_payload(token=token)
        user = self._check_user(payload=payload)
        user.jwt_secret = uuid.uuid4()
        user.save()
        # Get and check 'orig_iat'
        orig_iat = payload.get('orig_iat')

        if orig_iat:
            # Verify expiration
            refresh_limit = api_settings.JWT_REFRESH_EXPIRATION_DELTA

            if isinstance(refresh_limit, timedelta):
                refresh_limit = (refresh_limit.days * 24 * 3600 + refresh_limit.seconds)

            expiration_timestamp = orig_iat + int(refresh_limit)
            now_timestamp = timegm(datetime.utcnow().utctimetuple())

            if now_timestamp > expiration_timestamp:
                raise CommonException(code=codes.TOKEN_EXPIRED, detail=messages.REFRESH_HAS_EXPIRED)
        else:
            raise CommonException(code=codes.SERVER_ERROR,
                                  detail=messages.ORIG_IAD_FIELD_IS_REQUIRED)

        new_payload = jwt_payload_handler(user)
        new_payload['orig_iat'] = now_timestamp

        return {
            'token': jwt_encode_handler(new_payload),
            'user': user
        }
