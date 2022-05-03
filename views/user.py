"""
File of viewsets for user login, change profile, logout, user detail
"""
import uuid

from django.contrib.auth import get_user_model
from django.utils.decorators import method_decorator
from rest_framework import viewsets, generics
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.renderers import TemplateHTMLRenderer
from rest_framework.response import Response

from apps.auth_.models import FanDiscount
from apps.auth_.serializers import (RegistrationSerializer,
                                    UserSerializer, UserProfileSerializer)
from apps.utils import constants
from apps.utils.decorators import response_wrapper

User = get_user_model()


@method_decorator(response_wrapper(), name='dispatch')
class UserViewSet(viewsets.GenericViewSet):
    """
    ViewSet of user actions.

    ...
class
    Methods
    -------
    get_serializer_class(self)
        return serializer class regarding to action
    register(self, request)
        register user with full name and email
    get(self, request)
        returns user who authenticated (request.user)
    update_profile(self, request)
        update profile of user
    logout(self, request)
        deletes push tokens of user
    get_qr(self, request)
        return qr of user which is authenticated
    """
    queryset = User.objects.all()
    permission_classes = (IsAuthenticated,)
    http_method_names = ['get', 'put', 'post']
    serializer_class = UserSerializer

    def get_serializer_class(self):
        """
        Function will return serializer class regarding to action
        :return: class of Serializer
        """
        if self.action == 'register':
            return RegistrationSerializer
        if self.action == 'update_profile':
            return UserProfileSerializer
        return self.serializer_class
   
    @action(methods=['post'], detail=False)
    def register(self, request):
        """
        Complete registration with full name and email of user
        :return: changed data of registered user
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.complete_registration(request.user)
        return Response({'user': UserSerializer(request.user).data})

    @action(methods=['get', ], detail=False)
    def get(self, request):
        """
        Return data of user who is authenticated
        :return: data of user
        """
        return Response({'user': UserSerializer(request.user).data})

    @action(methods=['put'], detail=False)
    def update_profile(self, request):
        """
        Function to update profile of user
        :return: data of user
        """
        serializer = UserProfileSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.update(request.user, serializer.validated_data)
        return Response({'user': UserSerializer(request.user).data})

    @action(methods=['get'], detail=False)
    def logout(self, request):
        """
        Simulation of logout, delete all push tokens of user to don't send push when user logout
        :return:
        """
        # TODO: maybe several devices?
        request.user.push_tokens.all().delete()
        return Response({})

    @action(methods=['get', ], detail=False)
    def get_qr(self, request):
        """
        Return qr code of user if exists or create new and set to the user
        :return: qr of user
        """
        try:
            qrcode = request.user.qrcode
            uuid_str = qrcode.code
        except Exception:
            uuid_str = uuid.uuid4()
            qrcode = QrUserImage.objects.create(user=request.user,
                                                code=uuid_str)

        return Response({'qr': qrcode.get_url(uuid_str)})


class UserDetail(generics.RetrieveAPIView):
    """
    Class which render template and send to template discounts of user and where they work

    ...

    Methods
    -------
    get(self, request, code)
        return data related to user to template
    """
    renderer_classes = [TemplateHTMLRenderer]
    permission_classes = (AllowAny,)
    template_name = 'user/info.html'

    def get(self, request, code):  # noqa
        """
        Return code, user, company name, position and discounts with companies.
        :param request:
        :param code: code of user by what qr image made
        :return: data of user related to discounts
        """
        qr = QrUserImage.objects.get(code=code)
        user = qr.user
        user_companies = user.user_companies.all()
        company_name = ""
        company_position = ""
        company_discounts = {}
        if user.status == constants.EMPLOYEE:
            for user_company in user_companies:
                for company_discount in user_company.company_discount.all():
                    if company_discount.percent != 0 or \
                            company_discount.amount != 0:
                        temp = {'percent': company_discount.percent,
                                'amount': company_discount.amount,
                                'description': company_discount.description}
                        if not temp['description']:
                            temp['description'] = ''
                        if company_discount.company not in company_discounts.keys():
                            company_discounts[company_discount.company] = [temp]
                        else:
                            company_discounts[company_discount.company].append(temp)
                if user_company.isEmployer:
                    company_name = user_company.company.name
                    company_position = user_company.position
        else:
            for discount in FanDiscount.objects.all():
                for company_discount in discount.company_discounts.all():
                    if company_discount.percent != 0 or \
                            company_discount.amount != 0:
                        temp = {'percent': company_discount.percent,
                                'amount': company_discount.amount,
                                'description': company_discount.description}
                        if not temp['description']:
                            temp['description'] = ''
                        if company_discount.company not in company_discounts.keys():
                            company_discounts[company_discount.company] = [temp]
                        else:
                            company_discounts[company_discount.company].append(temp)
        return Response({'code': code, 'user': user,
                         'company_name': company_name,
                         'company_position': company_position,
                         'company_discounts': company_discounts})
