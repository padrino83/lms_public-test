from django.urls import path

from . import views

urlpatterns = [
    path('permission_denied/', views.permission_denied, name="permission_denied"),
    #Customer
    path('add_customer/', views.add_customer, name="add_customer"),
    path('customer/<uuid:pk>/edit/', views.edit_customer, name="edit_customer"),
    path('customers_list/', views.customers_list, name="customers_list"),
    path('customer_autocomplete/', views.CustomerAutocomplete.as_view(), name='customer_autocomplete'),
]
