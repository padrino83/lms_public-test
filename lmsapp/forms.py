from django.forms import ModelForm
from django import forms
from django.contrib.auth.models import User

from dal import autocomplete

from common.widgets import SelectWithPop

from common.models import Customer, Product

from .models import STATUS
from .models import Vehicle, Order, Load
from .models import Invoice, InvoiceOrder

# Create forms here.....


class VehicleForm(ModelForm):
    class Meta:
        model = Vehicle
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super(VehicleForm, self).__init__(*args, **kwargs)
        self.fields['driver'].widget.attrs = {'class': 'chosen-select', }


class OrderForm(ModelForm):
    #customer = forms.ModelChoiceField(Customer.objects.filter(active=True), required=False, widget=autocomplete.ModelSelect2(url='customer_autocomplete'))
    product = forms.ModelChoiceField(Product.objects.all(), required=False)
    pickup_location = forms.ModelChoiceField(Customer.objects.filter(active=True), empty_label=None, widget=autocomplete.ModelSelect2(url='customer_autocomplete'))
    dropoff_location = forms.ModelChoiceField(Customer.objects.filter(active=True), empty_label=None, widget=autocomplete.ModelSelect2(url='customer_autocomplete'))
    photob64 = forms.CharField(widget=forms.HiddenInput, required=False)

    class Meta:
        model = Order
        exclude = ('id', 'active', 'status', 'customer', 'date_order', 'added_by', 'total_amount', 'image', 'price')

    def __init__(self, *args, **kwargs):
        super(OrderForm, self).__init__(*args, **kwargs)
        #self.fields['customer'].widget.attrs = {'class': 'chosen-select', }
        self.fields['product'].widget.attrs = {'class': 'chosen-select', }
        #self.fields['pickup_location'].widget.attrs = {'class': 'chosen-select', }
        #self.fields['dropoff_location'].widget.attrs = {'class': 'chosen-select', }
        #self.fields['status'].widget.attrs = {'class': 'chosen-select', }


class LoadForm(ModelForm):
    vehicle = forms.ModelChoiceField(Vehicle.objects.filter(active=True), empty_label=None)
    photob64 = forms.CharField(widget=forms.HiddenInput, required=False)

    class Meta:
        model = Load
        exclude = ('id', 'order', 'customer', 'product', 'pickup_location', 'dropoff_location', 'driver', 'added_by', 'total_amount', 'total_driver_amount')

    def __init__(self, *args, **kwargs):
        super(LoadForm, self).__init__(*args, **kwargs)
        self.fields['vehicle'].widget.attrs = {'class': 'chosen-select', }


class DriverLoadForm(ModelForm):
    #customer = forms.ModelChoiceField(Customer.objects.filter(active=True), required=False, widget=autocomplete.ModelSelect2(url='customer_autocomplete'))
    pickup_location = forms.ModelChoiceField(Customer.objects.filter(active=True), empty_label=None, widget=autocomplete.ModelSelect2(url='customer_autocomplete'))
    dropoff_location = forms.ModelChoiceField(Customer.objects.filter(active=True), empty_label=None, widget=autocomplete.ModelSelect2(url='customer_autocomplete'))
    product = forms.ModelChoiceField(Product.objects.filter(active=True), empty_label=None)
    vehicle = forms.ModelChoiceField(Vehicle.objects.filter(active=True), empty_label=None)
    photob64 = forms.CharField(widget=forms.HiddenInput, required=False)

    class Meta:
        model = Load
        exclude = ('id', 'order', 'customer', 'driver', 'added_by', 'total_amount', 'total_driver_amount')

    def __init__(self, *args, **kwargs):
        super(DriverLoadForm, self).__init__(*args, **kwargs)
        #self.fields['customer'].widget.attrs = {'class': 'chosen-select', }
        self.fields['product'].widget.attrs = {'class': 'chosen-select', }
        #self.fields['pickup_location'].widget.attrs = {'class': 'chosen-select', }
        #self.fields['dropoff_location'].widget.attrs = {'class': 'chosen-select', }
        self.fields['vehicle'].widget.attrs = {'class': 'chosen-select', }


class OrderAddTicketForm(forms.Form):
    photob64 = forms.CharField(widget=forms.HiddenInput, required=False)


class searchForm(forms.Form):
    truck_number = forms.ModelChoiceField(Vehicle.objects.all(), required=False)
    driver = forms.ModelChoiceField(User.objects.all(), required=False)

    def __init__(self, *args, **kwargs):
        super(searchForm, self).__init__(*args, **kwargs)
        self.fields['truck_number'].label = 'TRUCK #'
        self.fields['truck_number'].widget.attrs = {'class': 'chosen-select', }
        self.fields['driver'].label = 'Driver'
        self.fields['driver'].widget.attrs = {'class': 'chosen-select', }


class search_order_customerForm(forms.Form):
    initial_date = forms.DateField(required=False)
    final_date = forms.DateField(required=False)

    def __init__(self, *args, **kwargs):
        super(search_order_customerForm, self).__init__(*args, **kwargs)
        self.fields['initial_date'].widget.attrs = {'class': 'form-control datepicker'}
        self.fields['final_date'].widget.attrs = {'class': 'form-control datepicker'}


class search_order_vehicleForm(forms.Form):
    driver = forms.ModelChoiceField(User.objects.filter(assigned_loads__isnull=False).distinct().exclude(is_superuser=True), required=False, empty_label='Choose a driver')
    product = forms.ModelChoiceField(Product.objects.all(), required=False)
    #start_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}), label='Start Date', required=False)
    start_date = forms.DateField(label='Start Date', required=False)
    #end_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}), label='End Date', required=False)
    end_date = forms.DateField(label='End Date', required=False)

    def __init__(self, *args, **kwargs):
        super(search_order_vehicleForm, self).__init__(*args, **kwargs)
        self.fields['start_date'].widget.attrs = {'class': 'form-control datepicker'}
        self.fields['end_date'].widget.attrs = {'class': 'form-control datepicker'}


class OrderFilterForm(forms.Form):
    q = forms.CharField(label='Search by Customer', required=False)
    driver = forms.ModelChoiceField(User.objects.all(), required=False)
    status = forms.ChoiceField(label='Status', choices=[('', 'Choose Status')] + [(v, k) for v, k in STATUS], required=False)
    date_start = forms.DateField(label='Start Date', required=False)
    date_end = forms.DateField(label='End Date', required=False)

    def __init__(self, *args, **kwargs):
        super(OrderFilterForm, self).__init__(*args, **kwargs)
        self.fields['date_start'].widget.attrs = {'class': 'form-control datepicker'}
        self.fields['date_end'].widget.attrs = {'class': 'form-control datepicker'}


class InvoiceForm(ModelForm):
    class Meta:
        model = Invoice
        exclude = ['total_amount', 'date_added']


class InvoiceOrderForm(ModelForm):
    class Meta:
        model = InvoiceOrder
        exclude = ['invoice']


class search_load_customerForm(forms.Form):
    q = forms.CharField(label='Search by Customer', required=False)
    driver = forms.ModelChoiceField(User.objects.all(), required=False)
    product = forms.ModelChoiceField(Product.objects.all(), required=False)
    date_start = forms.DateField(required=False)
    date_end = forms.DateField(required=False)

    def __init__(self, *args, **kwargs):
        super(search_load_customerForm, self).__init__(*args, **kwargs)
        self.fields['date_start'].widget.attrs = {'class': 'form-control datepicker'}
        self.fields['date_end'].widget.attrs = {'class': 'form-control datepicker'}
