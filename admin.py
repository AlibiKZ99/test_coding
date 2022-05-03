"""
Configurations of the models for admin panel.
"""
import xlwt
from daterangefilter.filters import PastDateRangeFilter
from apps.auth_.forms import (MainUserChangeForm,
                              MainUserCreationForm,
                              CompanyUserForm,
                              CompanyDiscountForm,
                              FanDiscountForm)
from apps.auth_.models import (Activation, MainUser, Company,
                               UserCompany, CompanyDiscount,
                               FanDiscount)
from dal import autocomplete
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.db.models import Q
from django.http import HttpResponse


class UserAutocomplete(autocomplete.Select2QuerySetView):
    """
    To search users by phone, full_name or username.

    ...

    Methods
    -------
    get_queryset(self)
        to search user by phone, full_name or username and autocomplete
    """
    def get_queryset(self):
        """
        To search user by phone, full_name or username and autocomplete
        :return: queryset of the users which is compatible with the request
        :rtype: queryset
        """
        if not all((self.request.user.is_authenticated,
                    self.request.user.is_staff)):
            return MainUser.objects.none()

        qs = MainUser.objects.all()

        if self.q:
            qs = qs.filter(
                Q(phone__icontains=self.q) | Q(full_name__icontains=self.q) | Q(
                    username__icontains=self.q)
            )

        return qs


class CompanyDiscountAutocomplete(autocomplete.Select2QuerySetView):
    """
    Class to search and autocomplete the entered request

    ...

    Methods
    -------
    get_queryset(self)
        Filter the queryset by entered company name ot description of the discount
    """
    def get_queryset(self):
        """
        Checks for the authentication and that the user is staff in the admin
        and search by companies' name and description of the discount
        :return: queryset of the companyDiscount model which is filtered by request
        :rtype: queryset of the class CompanyDiscount
        """
        if not all((self.request.user.is_authenticated,
                    self.request.user.is_staff)):
            return CompanyDiscount.objects.none()

        qs = CompanyDiscount.objects.all()

        if self.q:
            qs = qs.filter(
                Q(company__name__icontains=self.q) | Q(description__icontains=self.q)
            )

        return qs


@admin.register(MainUser)
class MainUserAdmin(UserAdmin):
    """
    Model admin for MainUser class.
    Setted creation form and change form of the user.
    Changed fields which will be represented in the list of the objects,
    in the change form and add form. Has filter by created date and search by username.

    ...

    Methods
    -------
    export_xlsx(self, request, queryset)
        custom action in the admin to export users in excel
    """
    form = MainUserChangeForm
    add_form = MainUserCreationForm
    list_filter = (('created_at', PastDateRangeFilter),)
    list_display = ('id', 'email', 'full_name')
    fieldsets = (
        ('Main Fields', dict(fields=(
            'username',
            'email',
            'full_name',
            'phone',
            'status',
        ))
        ),
        ('Password', {'fields': ('password',)}),
        ('Permissions',
         {'fields': ('groups', 'is_active', 'is_admin', 'is_staff',)}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email',)}
         ),
    )
    ordering = ['username']
    search_fields = ['username']
    actions = ['export_xlsx']

    def export_xlsx(self, request, queryset):
        """
        Function to export to excel file list of users.
        :param request: request of the action
        :param queryset: queryset of the users which the user picked in the admin
        :return: excel file
        """
        response = HttpResponse(content_type='application/ms-excel')
        response['Content-Disposition'] = 'attachment; filename="users.xls"'
        wb = xlwt.Workbook(encoding='utf-8')
        ws = wb.add_sheet('Пользователи')
        row_num = 0

        font_style = xlwt.XFStyle()
        font_style.font.bold = True

        columns = [
            "ID",
            "Почта",
            "Полное имя"
        ]

        for col_num in range(len(columns)):
            ws.write(row_num, col_num, columns[col_num], font_style)

        font_style = xlwt.XFStyle()

        for s in queryset:
            row_num += 1
            row = [
                s.id,
                s.email,
                s.full_name,
            ]
            for col_num in range(len(row)):
                ws.write(row_num, col_num, row[col_num], font_style)
        wb.save(response)
        return response

    export_xlsx.short_description = "Скачать данные"


@admin.register(Activation)
class ActivationAdmin(admin.ModelAdmin):
    """
    Model admin for Activation class.
    Setted fields which will be displayed in the list, filtered and searched by that fields
    """
    list_display = ('user', 'code', 'activation_type', 'is_active', )
    list_filter = ('activation_type', )
    search_fields = ['user']


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    """
    Company model admin to represents company objects with name.
    """
    list_display = ('name', )


@admin.register(UserCompany)
class UserCompanyAdmin(admin.ModelAdmin):
    """
    Model admin for representing relations between user, company and discounts of the companies.
    Form is setted to have fields wich will be with autocompletion and changed view of the
    objects in the table
    """
    form = CompanyUserForm
    list_display = ('user', 'company')
    fieldsets = (
        ('Main', {'fields': ('user', 'company', 'isEmployer', 'position')}),
        ('Discounts of companies', {'fields': ('company_discount',)})
    )


@admin.register(CompanyDiscount)
class CompanyDiscountAdmin(admin.ModelAdmin):
    """
    Model admin for class CompanyDiscount.
    Form is setted to have fields wich will be with autocompletion and changed view
    of the objects in the table
    """
    form = CompanyDiscountForm
    list_display = ('company', 'percent', 'amount', 'description')


@admin.register(FanDiscount)
class FanDiscountAdmin(admin.ModelAdmin):
    """
    Model admin for class FanDiscount to change representation in the admin.
    Form is setted to have fields wich will be with autocompletion and changed
    view of the objects in the table

    ...

    Methods
    -------
    get_company_discounts(self, obj)
        returns company name, discount and description
    """
    form = FanDiscountForm
    list_display = ('id', 'get_company_discounts')

    def get_company_discounts(self, obj):
        """
        Returns company name, discount in percent or tenge and description which is setted
        to the FanDiscount
        :param obj: FanDiscount object
        :return: string of the setted company discounts with name of the company,
        discount and description of the discount
        """
        company_discounts = ""
        for d in obj.company_discounts.all():
            company_discounts += f"{d.__str__()}, "
        return company_discounts
    get_company_discounts.short_description = "Скидки компании"
