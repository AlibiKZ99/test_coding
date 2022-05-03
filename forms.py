"""
File to change view of the admin panel.
"""
from dal import autocomplete
from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from apps.auth_.models import MainUser, UserCompany, CompanyDiscount, FanDiscount
from apps.utils import messages


class MainUserCreationForm(UserCreationForm):
    """
    Creation form for user in admin.

    ...

    Methods
    -------
    __init__(self, *args, **kwargs)
        function which will be done when starts to load the creation of user page
    """

    def __init__(self, *args, **kwargs):
        """
        In creation of user the password fields will not be required and will not autocomplete.
        """
        super(MainUserCreationForm, self).__init__(*args, **kwargs)
        self.fields['password1'].required = False
        self.fields['password2'].required = False
        # If one field gets autocompleted but not the other, our 'neither
        # password or both password' validation will be triggered.
        self.fields['password1'].widget.attrs['autocomplete'] = 'off'
        self.fields['password2'].widget.attrs['autocomplete'] = 'off'

    class Meta(UserCreationForm.Meta):
        model = MainUser
        fields = '__all__'


class MainUserChangeForm(UserChangeForm):
    """
    Form to change user in admin panel.

    ...

    Methods
    -------
    __init__(self, *args, **kwargs)
        function which will be done when starts to load the change user page
    """

    def __init__(self, *args, **kwargs):
        super(MainUserChangeForm, self).__init__(*args, **kwargs)

    class Meta(UserChangeForm.Meta):
        model = MainUser
        fields = '__all__'


class CompanyUserForm(forms.ModelForm):
    """
    Form of model UserCompany.
    User and company_discount fields in UserCompany model will be search field with autocomplete.
    Also changed the length of the field company_dicount.
    """

    class Meta:
        model = UserCompany
        fields = '__all__'

    user = forms.ModelChoiceField(
        queryset=MainUser.objects.all(), label="Сотрудник",
        widget=autocomplete.ModelSelect2(url='user-autocomplete'))

    company_discount = forms.ModelMultipleChoiceField(
        required=False, queryset=CompanyDiscount.objects.all(), label='Компании со скидками',
        widget=autocomplete.ModelSelect2Multiple(url='companydiscount-autocomplete',
                                                 attrs={'style': 'width: 45em;'})
    )


class FanDiscountForm(forms.ModelForm):
    """
    Form to change representation of model FanDiscount in admin panel.
    Company_discounts field in the model FanDiscount will be search field
    with autocomplete and length 45em.
    """
    class Meta:
        model = FanDiscount
        fields = '__all__'

    company_discounts = forms.ModelMultipleChoiceField(
        queryset=CompanyDiscount.objects.all(), label='Компании со скидками',
        widget=autocomplete.ModelSelect2Multiple(url='companydiscount-autocomplete',
                                                 attrs={'style': 'width: 45em;'})
    )


class CompanyDiscountForm(forms.ModelForm):
    """
    Form for model CompanyDiscount to validate the data in the admin panel.

    ...

    Methods
    -------
    clean(self):
        checks the validity of the fields percent and amount
    """
    class Meta:
        model = CompanyDiscount
        fields = '__all__'

    def clean(self):
        """
        Function to validate the fields percent and amount in order to check if there
        is field is empty or both of them are not empty.
        :return: data of the CompanyDiscount model which is entered from the admin
        :rtype: json
        """
        if self.cleaned_data['percent'] and self.cleaned_data['amount']:
            self.add_error('amount', messages.PERCENT_OR_AMOUNT)
        elif self.cleaned_data['percent'] is None:
            self.add_error('percent', messages.PERCENT_NULL)
        elif self.cleaned_data['amount'] is None:
            self.add_error('amount', messages.PERCENT_NULL)
        return self.cleaned_data
