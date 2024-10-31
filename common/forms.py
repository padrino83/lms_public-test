from django import forms
from django.forms import ModelForm
from django.contrib.auth.models import User

from .models import UserProfile
from .models import Customer, UnitMeasurement, Product


class UserForm(ModelForm):
    """User form."""
    password = forms.CharField(widget=forms.PasswordInput)
    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email']
    
    def __init__(self, *args, **kwargs):
        super(UserForm, self).__init__(*args, **kwargs)
        self.fields['first_name'].required = True
        self.fields['last_name'].required = True


class UserEditForm(ModelForm):
    """User form."""
    class Meta:
        model = User
        fields = ['first_name', 'last_name']
    
    def __init__(self, *args, **kwargs):
        super(UserEditForm, self).__init__(*args, **kwargs)
        self.fields['first_name'].required = True
        self.fields['last_name'].required = True


class UserProfileForm(ModelForm):
    """User profile form."""
    class Meta:
        model = UserProfile
        exclude = ['user', 'show_earned']


class ContactForm(forms.Form):
    """Contact form."""
    name = forms.CharField(label=u"Nombre")
    email = forms.EmailField(label=u'Email')
    message = forms.CharField(widget=forms.Textarea, label='Mensaje')
    # captcha = CaptchaField(help_text=u"Resuelva esta cuenta para comprobar que no es un robot.")


class CustomerForm(ModelForm):
    class Meta:
        model = Customer
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super(CustomerForm, self).__init__(*args, **kwargs)


class ProductForm(ModelForm):
    class Meta:
        model = Product
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super(ProductForm, self).__init__(*args, **kwargs)
        self.fields['unitmeasurement'].widget.attrs = {'class': 'chosen-select', }
        self.fields['price'].widget.attrs = {'class': 'chosen-select', }


class UnitMeasurementForm(ModelForm):
    class Meta:
        model = UnitMeasurement
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super(UnitMeasurementForm, self).__init__(*args, **kwargs)
