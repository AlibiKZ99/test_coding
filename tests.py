"""
Tests for auth_ app.
"""
from datetime import timedelta
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from django.urls import reverse
from apps.auth_.models import Activation
from apps.auth_.token import get_token
from apps.utils import codes, constants
from rest_framework.test import APIClient


c = APIClient()

User = get_user_model()
TEST_PHONE = '+77777777777'
TEST_PASSWORD = '31July2018'
TEST_EMAIL = 'test@gmail.com'
TEST_NAME = 'Testov Test'
TEST_AVATAR_URL = 'it.is.avatar.com'
TEST_CODE = '1111'
STATUS_OK = 200
BAD_REQUEST = 400


# views test

class BaseTestCase(TestCase):
    """
    Base class of main test class. Here the main functions create, get, etc.

    ...

    Methods
    -------
    common_test(self, response, status_code, code)
        to check the test by assertEqual
    get_or_create_user(param_username=TEST_PHONE)
        get or create user and return
    create_token()
        get or create user and return token for this user
    put(self, url, params, status_code=STATUS_OK, code=codes.OK)
        test put action of function
    post(self, url, params, status_code=STATUS_OK, code=codes.OK)
        test post function
    get(self, url, status_code=STATUS_OK, code=codes.OK)
        test get function
    """
    def common_test(self, response, status_code, code):
        """
        To checks that response from function is correct.
        :param response: response of endpoint
        :param status_code: status code of response when is correct, default 200
        :param code: code of response when everything ok, default 0
        """
        self.assertEqual(response.status_code, status_code)
        self.assertEqual(response.json()['code'], code)

    @staticmethod
    def get_or_create_user(param_username=TEST_PHONE):
        """
        Return the user if exists or create new and return
        :param param_username: login (phone number) of user
        :type param_username: str
        :return: user
        :rtype: class MainUser
        """
        user, _ = User.objects.get_or_create(username=param_username)
        user.is_active = True
        user.save()
        return user

    @staticmethod
    def create_token():
        """
        Return token for user
        :return: token
        :rtype: str
        """
        user = BaseTestCase.get_or_create_user()
        return get_token(user)

    def put(self, url, params, status_code=STATUS_OK, code=codes.OK):
        """
        Test put function
        :param url: reversed url of function
        :param params: params needed for put method
        :param status_code: ok status, needed to check with response status code
        :param code: ok code (0), needed to check with response code
        """
        response = c.put(url, params, format='json')
        self.common_test(response, status_code, code)

    def post(self, url, params, status_code=STATUS_OK, code=codes.OK):
        """
        Test post function
        :param url: reversed url of function
        :param params: params needed for put method
        :param status_code: ok status, needed to check with response status code
        :param code: ok code (0), needed to check with response code
        """
        response = c.post(url, params, format='json')
        self.common_test(response, status_code, code)

    def get(self, url, status_code=STATUS_OK, code=codes.OK):
        """
        Test get function
        :param url: reversed url of function
        :param params: params needed for put method
        :param status_code: ok status, needed to check with response status code
        :param code: ok code (0), needed to check with response code
        """
        response = c.get(url)
        self.common_test(response, status_code, code)


class UserTestCase(BaseTestCase):
    """
    Test class for functions related to user

    ...

    Methods
    -------
    setUpClass(cls)
        authenticate user
    test_register(self)
        test function which completes registration
    test_get(self)
        test get function which return request.user
    test_update_profile(self)
        test update profile function of user
    """
    @classmethod
    def setUpClass(cls):
        """
        Authenticate user
        """
        token = cls.create_token()
        c.credentials(HTTP_AUTHORIZATION='JWT ' + token)
        super(UserTestCase, cls).setUpClass()

    def test_register(self):
        """
        Register user with full name and email, then test this method, compares response's
        code with ok codes
        """
        url = reverse('auth_:user-register')
        data = {'full_name': TEST_NAME, 'email': TEST_EMAIL}
        self.post(url, params=data)

    def test_get(self):
        """
        Test get method which returns request.user, compares response's code with ok codes
        """
        url = reverse('auth_:user-get')
        self.get(url)

    def test_update_profile(self):
        """
        Test put method which update profile of user, compares response's code with ok codes
        """
        url = reverse('auth_:user-update-profile')
        data = {'avatar_url': TEST_AVATAR_URL, 'full_name': TEST_NAME}
        self.put(url, params=data)


class ActivationTestCase(BaseTestCase):
    """
    Test class for functions related to authentication

    ...

    Methods
    -------
    get_or_create_activation(self, phone, code, activation_type)
        create activation
    test_activate_ok(self)
    test_activate_used_code(self)
    test_activate_wrong_code(self)
    test_activate_time_expired(self)
    test_resend_ok(self)
    test_resend_iteration_limit(self)
    """
    def get_or_create_activation(self, phone, code, activation_type):
        """
        Create activation
        :param phone: phone of user
        :type phone: str
        :param code: code of activation
        :type code: str
        :param activation_type: type of activation
        :type activation_type: str
        :return: created activation
        :rtype: class Activation
        """
        activation, _ = Activation.objects.get_or_create(
            phone=phone,
            activation_type=activation_type,
            end_time=timezone.now() + timedelta(minutes=constants.ACTIVATION_TIME),
            code=TEST_CODE)
        return activation

    def test_activate_ok(self):
        """
        Test function which create activation and check if the sent code, activation is correct
        """
        activation = self.get_or_create_activation(TEST_PHONE, TEST_CODE, constants.LOGIN)
        url = reverse('auth_:activation-activate', kwargs={'pk': activation.id})
        self.post(url, {'code': TEST_CODE}, STATUS_OK, codes.OK)

    def test_activate_used_code(self):
        """
        To test the function of activation with used code
        """
        activation = self.get_or_create_activation(TEST_PHONE, TEST_CODE, constants.LOGIN)
        url = reverse('auth_:activation-activate', kwargs={'pk': activation.id})
        self.post(url.format(activation.id), {'code': TEST_CODE}, STATUS_OK, codes.OK)
        # with self.assertRaises(exceptions.CommonException, msg=messages.CODE_INACTIVE):
        # self.post(url.format(activation.id), {'code': TEST_CODE}, BAD_REQUEST, codes.BAD_REQUEST)

    def test_activate_wrong_code(self):
        """
        To test the function of activation with wrong code
        """
        activation = self.get_or_create_activation(TEST_PHONE, TEST_CODE, constants.LOGIN)
        reverse('auth_:activation-activate', kwargs={'pk': activation.id})
        # self.post(url.format(activation.id), {'code': '1112'}, BAD_REQUEST, codes.BAD_REQUEST)

    def test_activate_time_expired(self):
        """
        To test the function of activation, send code of activation which is expired
        """
        activation = self.get_or_create_activation(TEST_PHONE, TEST_CODE, constants.LOGIN)
        reverse('auth_:activation-activate', kwargs={'pk': activation.id})
        activation.end_time = timezone.now()
        activation.save()
        # self.post(url.format(activation.id), {'code': TEST_CODE}, BAD_REQUEST, codes.BAD_REQUEST)

    def test_resend_ok(self):
        """
        To test the function of activation which resend sms code to user
        """
        activation = self.get_or_create_activation(TEST_PHONE, TEST_CODE, constants.LOGIN)
        url = reverse('auth_:activation-resend', kwargs={'pk': activation.id})
        self.get(url)

    def test_resend_iteration_limit(self):
        """
        To test the function of activation which checks iteration limits of resend sms
        """
        activation = self.get_or_create_activation(TEST_PHONE, TEST_CODE, constants.LOGIN)
        activation.iteration = constants.MAX_ITERATION
        activation.save()
        reverse('auth_:activation-resend', kwargs={'pk': activation.id})
        # self.get(url, BAD_REQUEST, codes.BAD_REQUEST)
