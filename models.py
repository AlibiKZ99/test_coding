"""
This file keeps definitions of user, activation and discounts with company.
"""
from datetime import timedelta
from django.conf import settings
from django.contrib.auth.models import (BaseUserManager, AbstractBaseUser,
                                        PermissionsMixin)
from django.db import models
from django.utils import timezone
from apps.utils import constants, messages
from apps.auth_.validators import phone_validator, full_name_validator
from apps.utils.exceptions import CommonException
from apps.utils.password import generate_sms_code
from apps.utils.image_utils import resize_image_proportionally
from apps.utils.sms import send_sms_code
import uuid
import logging

from apps.utils.upload import unique_path

logger = logging.getLogger(__name__)


def jwt_get_secret_key(user_model):
    """
    Function for returning token of certain user which in parameters
    :param user_model: get object of MainUser model
    :type user_model: class MainUser
    :return: returns JWT token of user object
    :rtype: UUID
    """
    return user_model.jwt_secret


class MainUserManager(BaseUserManager):
    """
    Main user manager.
    Keeps functions which we can use in model writing
    name_of_class.objects.name_of_function(send_related_params)

    ...

    Methods
    -------
    create_user(self, username, phone=None, email=None,
                password=None)
        create user with taken username phone, email, encrypted password
        and return created user
    create_superuser(self, username, password)
        create superuser with username, password for managing django admin
        (passwords are saved in encrypted way)
    """

    def create_user(self, username, phone=None, email=None,
                    password=None):
        """
        Creates and saves a user with the given username, phone, email.
        Set the password, but before encrypt it and then save.
        If the username is not sent to function then raise ValueError exception
        :param username: username of user
        :type username: str
        :param phone: phone of user
        :type phone: str
        :param email: email of user
        :type email: str
        :param password: password of user for authentication
        :type password: str
        :raises: :class:`ValueError`: username is not sent to function
        :return: returns created user
        :rtype: class MainUser
        """
        if not username:
            raise ValueError('User must have a username')
        user = self.model(username=username, phone=phone,
                          email=email)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, password):
        """
        Creates and saves a superuser with the given phone and password.
        Make this user admin, superuser, moderator, staff.
        :param username:  username of user for authentication
        :type username: str
        :param password: password of user for authentication
        :type password: str
        :return: created user
        :rtype: class MainUser
        """
        user = self.create_user(username=username, password=password)
        user.is_admin = True
        user.is_superuser = True
        user.is_moderator = True
        user.is_staff = True
        user.save(using=self._db)
        return user


class MainUser(AbstractBaseUser, PermissionsMixin):
    """
    A class used to represent an User.

    ...

    Attributes
    ----------
    username: str
        username of user for authentication (unique)
    full_name: str
        full name of user, namely firstname and lastname
        (has validator which checks that it contains only letters)
    avatar_url: str
        url of avatar in the profile
    phone: str
        phone of user (has validator that checks
        if there is such phone using phonenumbers library)
    email: str
        email of user
    timestamp: date
        keeps date and time when last update did in objects of MainUser model;
        set value automatically (auto_now=True)
    created_at: date
        keeps date and time when object is created;
        change value automatically (auto_now_add=True)
    status: str
        shows status of users: fan or employee (default=FAN)
    is_active: bool
        shows if the user is active or not (default=True)
    is_admin: bool
        admin or not in django admin (default=False)
    is_staff: bool
        if true, can login to django admin, and vice versa (default=False)
    birth_date: date
        birth day of user
    jwt_secret: UUID
        jwt token of user for authentication, by default set unique value using library uuid
    is_registered: bool
        keeps value if the user is registered or not (default=False)
    activations.all: queryset of class Activation
        activations (keeps data, code which is necessary to authenticate) of user
    company_users.all: queryset of class UserCompany
        list of objects which keeps relationships between user and company, company_discounts
    Methods
    -------
    __str__(self)
        returns phone of user
    """
    username = models.CharField(max_length=100, db_index=True, unique=True,
                                null=False, verbose_name='Пользователь')
    full_name = models.CharField(max_length=255, blank=True,
                                 null=True, validators=[full_name_validator],
                                 verbose_name='Полное имя')
    avatar_url = models.CharField(max_length=555, blank=True, null=True)
    phone = models.CharField(max_length=50, blank=True, null=True,
                             validators=[phone_validator], verbose_name='Телефон')
    email = models.EmailField(max_length=50, blank=True, null=True, verbose_name='Почта')
    timestamp = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True,
                                      verbose_name="Время создания")
    status = models.CharField(max_length=100, choices=constants.USER_STATUSES,
                              default=constants.FAN, verbose_name="Статус")
    is_active = models.BooleanField(default=True, verbose_name='Активность')
    is_admin = models.BooleanField(default=False)
    is_staff = models.BooleanField(default=False, verbose_name='Сотрудник')
    birth_date = models.DateField(blank=True, null=True)
    jwt_secret = models.UUIDField(default=uuid.uuid4)
    is_registered = models.BooleanField(default=False)
    objects = MainUserManager()
    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = []

    def __str__(self):
        """
        Returns phone of user when calls user object
        :return: phone of user
        :rtype: str
        """
        return '{}'.format(self.phone)


class ActivationManager(models.Manager):
    """
    Manager for activation keys.

    ...

    Methods
    -------
    generate_sms(self, phone, user=None,
                 activation_type=constants.LOGIN)
        send sms code and saves it in order to when user enter code to check it
    generate(self, user=None, phone=None,
             activation_type=constants.LOGIN)
        to check if there is created activation object for the certain user
        and if not create and send sms code
    """

    def generate_sms(self, phone, user=None,
                     activation_type=constants.LOGIN):
        """
        Creates activation object with params which written in brackets
        (by default user is None and activation type LOGIN) and send
        generated sms code to phone which is in params
        :param phone: phone (login) of user
        :type phone: str
        :param user: certain existing user in the database (can be not sent to params)
        :type user: class MainUser
        :param activation_type: activation type of authorization, there is only one type: by login
        :type activation_type: str
        :return: created activation
        :rtype: class Activation
        """
        activation = self.model(phone=phone, user=user)
        activation.user = user
        activation.activation_type = activation_type
        activation.end_time = timezone.now() + timedelta(
            minutes=constants.ACTIVATION_TIME)
        activation.code = generate_sms_code()
        activation.save()
        activation.send_sms(iterate=False)
        return activation

    def generate(self, user=None, phone=None,
                 activation_type=constants.LOGIN):
        """
        Returns activation object if object exists with the phone which is written
        or create activation, send sms code and return this activation
        :param user: MainUser object (can be not sent to params)
        :type user: class MainUser
        :param phone: phone of user (can be not sent to params)
        :type phone: str
        :param activation_type: type of activation of account (default by login)
        :type activation_type: str
        :return: activation which exists or created
        :rtype: class Activation
        """
        try:
            activation = self.get(phone=phone,
                                  user=user,
                                  timestamp__gt=timezone.now() - timedelta(
                                      minutes=constants.ACTIVATION_MIN),
                                  is_active=True,
                                  activation_type=activation_type)
            return activation
        except Activation.DoesNotExist:
            activation = self.generate_sms(phone=phone, user=user,
                                           activation_type=activation_type)
        return activation


class Activation(models.Model):
    """
    Model for storing activation keys.

    ...

    Attributes
    ----------
    user: class MainUser
        Each MainUser object has activation which holds sms code to login to the app
    phone: str
        phone of user
    code: str
        generated code which will be sent to phone of user
    end_time: date
        from now + 30 minutes;
        each activation has 30 minutes which means after that user can't enter code which
        sent 30 minutes ago
    timestamp: date
        keeps date and time when object is created;
        set value automatically (auto_now=True)
    activation_type: str
        type of authentication, default by login
    is_active: bool
        shows if the activation is active, if not then user can't authenticate
    iteration: int
        keeps number of sent sms codes to user
    user_companies: queryset of class UserCompany
        l

    Methods
    -------
    is_valid(self, raise_exception=False, data=None, check_iteration=False)
        checks that activation is active and entered code is correct
    complete(self, request=None)
        complete registration of user, sets appropriate values from activation to user object
    send_sms(self, iterate=True)
        send sms code to user's phone and iterate each sent sms if iterate param is true
    __str__(self)
        prints phone
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True,
                             related_name='activations',
                             on_delete=models.CASCADE, verbose_name='Пользователь')
    phone = models.CharField(max_length=20, null=True, verbose_name='Телефон')
    code = models.CharField(max_length=50, verbose_name='Код')
    end_time = models.DateTimeField(blank=True, null=True, verbose_name='Время окончания')
    timestamp = models.DateTimeField(auto_now=True)
    activation_type = models.CharField(max_length=20, choices=constants.ACTIVATION_TYPES,
                                       default=constants.LOGIN, verbose_name='Тип активаций')
    is_active = models.BooleanField(default=True, verbose_name='Активность')
    iteration = models.PositiveIntegerField(default=0, verbose_name='Количество попыток')
    objects = ActivationManager()

    def is_valid(self, raise_exception=False, data=None, check_iteration=False):
        """
        Checks if the activation is active, not expired,
        amount of sent sms isn't more than iteration field.
        Also checks if the written code by user is correct.
        Raise exceptions if the raise_exception param is True.
        :param raise_exception: if true, raise custom written exception with certain message
        :type raise_exception: bool
        :param data: written data by user
        :type data: json
        :param check_iteration: if true, then check iteration of amount of sent sms codes
        :type check_iteration: bool
        :return: if there is no any errors, return True, None, else if raise_exception false,
        then return False, error_message, else raise exception
        :rtype: tuple
        """
        if self.end_time < timezone.now():
            if raise_exception:
                raise CommonException(detail=messages.CODE_EXPIRED)
            return False, messages.CODE_EXPIRED
        if data and self.code != data['code']:
            if raise_exception:
                raise CommonException(detail=messages.CODE_NOT_CORRECT)
            return False, messages.CODE_INACTIVE
        if not self.is_active:
            if raise_exception:
                raise CommonException(detail=messages.CODE_INACTIVE)
            return False, messages.CODE_INACTIVE
        if check_iteration and self.iteration >= constants.MAX_ITERATION:
            if raise_exception:
                raise CommonException(detail=messages.MAX_ITERATION_EXCEED)
            return False, messages.MAX_ITERATION_EXCEED
        return True, None

    def complete(self, request=None):
        """
        Function to complete registration, get user form the database or create and set
        the values from the activation to the user.
        :param request: send request from the view
        :type request: json
        :return: got or created user and boolean value which means if the user created or not
        :rtype: tuple of class MainUser and bool
        """
        user, created = MainUser.objects.get_or_create(username=self.phone, is_active=True)
        user.phone = self.phone
        user.save()
        if created:
            user.is_registered = False
            user.save()
        self.user = user
        self.is_active = False
        self.save()
        return self.user, created

    def send_sms(self, iterate=True):
        """
        Function generates the code and send to entered phone. If in environment variables
        SMS_ON false or if entered phone number is in the tuple then sms will not be sent,
        code will be 1111. If iterate param is True, function will count each sent sms to
        validate then.
        :param iterate: shows should the function iterate each sent sms
        :type iterate: bool
        """
        if iterate:
            self.iteration += 1
            self.save()
        if not settings.SMS_ON or self.phone in ('+77787884230',):
            self.code = '1111'
            self.save()
        else:
            self.code = generate_sms_code(4)
            send_sms_code(self.phone, self.code)
        self.save()

    def __str__(self):
        """
        Prints phone of user
        :return: phone of user
        :rtype: str
        """
        return '{}'.format(self.phone)


class Company(models.Model):
    """
    Represents company entity with name, address, description and logo.

    ...

    Attributes
    ----------
    name: str
        name of the company
    description: str
        description of the company, what kind of company, what they do etc.
    address: str
        address of the company, where they are located
    image: image
        logo of the company, will be uploaded in the unique path
    company_discounts.all: queryset of class CompanyDiscount
        list of discounts of the company
    company_users.all: queryset of class UserCompany
        list of objects which keeps relationships between user and company, company_discounts

    Methods
    -------
    __str__(self)
        returns name of the company
    save(self, force_insert=False, force_update=False, using=None, update_fields=None)
        overriden save function to resize image proportionally
    """
    name = models.CharField(max_length=100, null=False, blank=False,
                            verbose_name='Компания')
    description = models.CharField(max_length=200, blank=True, null=True,
                                   verbose_name='Описание компании')
    address = models.CharField(max_length=100, null=True,
                               blank=True, verbose_name='Адрес')
    image = models.ImageField(upload_to=unique_path, verbose_name='Лого',
                              blank=True)

    class Meta:
        verbose_name = "Компания"
        verbose_name_plural = "Компании"

    def __str__(self):
        """
        Returns the name of the company.
        :return: name of the company
        :rtype: str
        """
        return '{}'.format(self.name)

    def save(self, force_insert=False, force_update=False, using=None, update_fields=None):
        """
        Override default save function in order to resize logo of the company proportionally.
        Takes unchanged company (before save takes company by id) then compare with changed
        version, if the changed version of the company object has image and image is changed,
        then resize image.If there is no company (created) then just checks that image is not none
        then if not resize it.

        There are default params of save function.
        """
        try:
            previous = Company.objects.get(id=self.id)
            super().save(force_insert=force_insert, force_update=force_update,
                         using=using, update_fields=update_fields)
            if self.image and previous.image != self.image:
                resize_image_proportionally(self.image.path, self.image.width, self.image.height)
        except Company.DoesNotExist:
            super().save(force_insert=force_insert, force_update=force_update,
                         using=using, update_fields=update_fields)
            if self.image:
                resize_image_proportionally(self.image.path, self.image.width,
                                            self.image.height)


class CompanyDiscount(models.Model):
    """
    Company has several discounts and this model for storing data for discount of company.

    ...

    Attributes
    ----------
    uuid: UUID
        unique id of object, default is uuid.uuid4, use library uuid which generates unique ids
    company: class Company
        foreign key of company object, shows to which company this discount is related
    percent: int
        amount of discount in percent
    amount: int
        amount of discount in tenge (default=0)
    description: str
        description or name of the discount (default=0)
    company_discount_users.all: queryset of class UserCompany
        list of objects of UserCompany model which keeps relationships
        between user companies discount and company

    Methods
    -------
    __str__(self)
        print name of the company, description and discount
    """
    uuid = models.UUIDField(default=uuid.uuid4, unique=True, verbose_name='Идентификатор')
    company = models.ForeignKey(Company, on_delete=models.CASCADE,
                                related_name='company_discounts',
                                verbose_name='Компания')
    percent = models.PositiveIntegerField(default=0, blank=True,
                                          verbose_name='Скидка (процент)')
    amount = models.PositiveIntegerField(default=0, blank=True,
                                         verbose_name="Скидка (сумма)")
    description = models.CharField(max_length=200, verbose_name='Описание скидки',
                                   blank=True, null=True)

    class Meta:
        verbose_name = "Скидка компании"
        verbose_name_plural = "Скидки компаний"

    def __str__(self):
        """
        Print the name of the company, description and discount of the CompanyDiscount object.
        If there is discount in percent then prints percent and if amount in tenge,
        prints tenge
        :return: company name, description and dicount in percent or amount
        :rtype: str
        """
        if self.percent:
            return f'{self.company}: {self.description} - {self.percent}%'
        else:
            return f'{self.company}: {self.description} - {self.amount}тг'


class UserCompany(models.Model):
    """
    Represents realtionship betweeen user and company, discounts of company.
    user: class MainUser
        user who has discounts or works in company
    company: class Company
        keeps company where user works
    company_discount: class CompanyDiscount
        list of discounts of some companies
    isEmployer: bool
        shows that the user works somewhere
    position: str
        position of the user in the company where he works

    Methods
    -------
    __str__(self)
        prints phone number of the user and company name
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=False,
                             related_name='user_companies',
                             on_delete=models.CASCADE,
                             verbose_name='Сотрудники')
    company = models.ForeignKey(Company, blank=True, null=True,
                                on_delete=models.CASCADE,
                                related_name="company_users",
                                verbose_name="Компания")
    company_discount = models.ManyToManyField(CompanyDiscount, blank=True,
                                              related_name='company_discount_users',
                                              verbose_name='Компании со скидками')
    isEmployer = models.BooleanField(default=False)
    position = models.CharField(max_length=500, blank=True, null=True,
                                verbose_name='Должность')

    class Meta:
        verbose_name = "Компании сотрудника"
        verbose_name_plural = "Компании сотрудника"

    def __str__(self):
        """
        Prints phone number of the user and company name where user works
        :return: phone of the user and company name
        :rtype: str
        """
        return 'Сотрудник: {}, Компания: {}'.format(
            self.user, self.company)


class FanDiscount(models.Model):
    """
    Model which represents discounts of some companies for users with status FAN

    ...

    Attributes
    ----------
    company_discounts: queryset of class Company
        list of discounts of several companies for fans

    Methods
    -------
    __str__(self)
        prints all companies discounts
    """
    company_discounts = models.ManyToManyField(CompanyDiscount,
                                               related_name='company_discounts_fans',
                                               verbose_name="Скидки компании")

    class Meta:
        verbose_name = "Скидка для болельщиков"
        verbose_name_plural = "Скидки для болельщиков"

    def __str__(self):
        """
        Prints all companies discounts. Go through list of  company discounts
        and add to string compamy's name, description and discount
        :return: all companies discounts
        :rtype: str
        """
        res = ""
        for d in self.company_discounts.all():
            res += f"{d.__str__()}, "
        return res
