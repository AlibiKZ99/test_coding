"""
Views for taking, refreshing token for authentication.
"""
from django.contrib.auth import get_user_model
from django.utils.decorators import method_decorator
from rest_framework.response import Response
from rest_framework_jwt.views import ObtainJSONWebToken, \
    jwt_response_payload_handler, RefreshJSONWebToken
from apps.auth_.serializers import CustomRefreshJSONWebTokenSerializer

from apps.utils import messages
from apps.utils.decorators import response_wrapper
from apps.utils.exceptions import CommonException
from django.utils.translation import gettext as _

User = get_user_model()


@method_decorator(response_wrapper(), name='dispatch')
class TokenView(ObtainJSONWebToken):
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)

        if serializer.is_valid(raise_exception=True):
            user = serializer.object.get('user') or request.user
            token = serializer.object.get('token')
            response_data = jwt_response_payload_handler(token, user, request)
            response = Response(response_data)
            return response
        raise CommonException(detail=_(messages.BAD_DATA))


@method_decorator(response_wrapper(), name='dispatch')
class RefreshTokenView(RefreshJSONWebToken):
    serializer_class = CustomRefreshJSONWebTokenSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        token = serializer.object.get('token')
        return Response({'token': token})
