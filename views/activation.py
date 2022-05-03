"""
File to keep viewsets for activation.
"""
from django.utils.decorators import method_decorator

from apps.auth_.models import Activation
from apps.auth_.serializers import ActivationCodeSerializer, PhoneSerializer, \
    ActivationSerializer, UserSerializer
from apps.auth_.token import get_token
from apps.utils.constants import (LOGIN)
from apps.utils.decorators import response_wrapper

from rest_framework.decorators import action
from rest_framework import mixins, viewsets
from rest_framework.permissions import AllowAny
from rest_framework.response import Response


@method_decorator(response_wrapper(), name='dispatch')
class ActivationViewSet(mixins.CreateModelMixin, viewsets.GenericViewSet):
    """
    ViewSet to create activation and send message, resend message and complete activation.

    ...

    Methods
    -------
    get_serializer_class(self)
        to return serializer class regarding to the action
    create(self, request, *args, **kwargs)
        create activation and send sms code to phone
    activate(self, request, pk=None)
        complete authentication
    resend(self, request, pk=None)
        resend sms code if the user didn't get
    """
    queryset = Activation.objects.all()
    http_method_names = ['post', 'get']
    permission_classes = (AllowAny,)

    def get_serializer_class(self):
        """
        Return serializer class regarding to action
        :return: serializer class
        """
        if self.action == 'activate':
            return ActivationCodeSerializer
        if self.action == 'create':
            return PhoneSerializer
        return ActivationSerializer

    def create(self, request, *args, **kwargs):
        """
        Create activation by phone and send sms
        :param request:
        :param *args:
        :param **kwargs:
        :return: created activation
        """
        serializer = PhoneSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        activation = Activation.objects.generate(
            phone=serializer.validated_data['phone'],
            activation_type=LOGIN)
        return Response({'activation': ActivationSerializer(activation).data})

    @action(methods=['post'], detail=True, permission_classes=[AllowAny])
    def activate(self, request, pk=None):
        """
        Activate the authentication by checking activation and entered code
        :param request: request of the action
        :param pk: id of the Activation object
        :return: jwt token of the user, user's data, boolean value which says that user created
        """
        serializer = ActivationCodeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        activation = self.get_object()
        activation.is_valid(raise_exception=True,
                            data=serializer.validated_data)
        user, created = activation.complete(request=request)
        user.save()
        token = get_token(user)
        return Response({'token': token,
                         'user': UserSerializer(user).data,
                         'new_user': created})

    @action(methods=['get'], detail=True, permission_classes=[AllowAny])
    def resend(self, request, pk=None):
        """
        Resend sms code to user
        :param request: request of action
        :param pk: id of Activation object
        :return: activation with pk and changed data
        """
        activation = self.get_object()
        activation.is_valid(raise_exception=True, check_iteration=True)
        activation.send_sms()
        return Response({'activation': ActivationSerializer(activation).data})
