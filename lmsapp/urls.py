from django.urls import path
from django.conf import settings
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.conf.urls.static import static

from . import views


urlpatterns = [
    path('index/', views.index, name="index"),
    #Order
    path('order/<uuid:pk>/autoassign/', views.autoassign_order, name="autoassign_order"),
    #path('drivers_list/', views.drivers_list, name="drivers_list"),
    path('orders_list/', views.orders_list, name="orders_list"),
    path('add_order/', views.add_order, name="add_order"),
    path('order/<uuid:pk>/', views.order_details, name="order_details"),
    path('order/<uuid:pk>/add_ticket/', views.order_add_ticket, name="order_add_ticket"),
    path('order/<uuid:pk>/edit/', views.edit_order, name="edit_order"),
    path('order/<uuid:pk>/delete/', views.order_delete, name="order_delete"),
    path('order/<uuid:pk>/clone/', views.order_clone, name="order_clone"),
    #Load
    path('loads_list/', views.loads_list, name="loads_list"),
    path('load/driver_add_load/', views.driver_add_load, name="driver_add_load"),
    path('order/<uuid:pk>/add_load/', views.add_load, name="add_load"),
    path('load/<uuid:pk>/', views.load_details, name="load_details"),
    path('load/<uuid:pk>/add_ticket/', views.load_add_ticket, name="load_add_ticket"),
    path('load/<uuid:pk>/edit/', views.edit_load, name="edit_load"),
    path('load/<uuid:pk>/delete/', views.load_delete, name="load_delete"),
    #Invoice
    path('invoice/', views.InvoiceDatatableView.as_view(), name='invoice_list'),
    path('invoice/new/', views.add_invoice, name="add_invoice"),
    path('invoice/<uuid:pk>/', views.invoice_details, name="invoice_details"),
    path('invoice/<uuid:pk>/barcode/', views.invoice_show_barcode, name="invoice_show_barcode"),
    path('invoice/<uuid:pk>/to_excel/', views.invoice_to_excel, name="invoice_to_excel"),
    #Report
    # path('report_orders_per_customer', views.report_orders_per_customer, name="report_orders_per_customer"),
    path('report_loads_by_driver/', views.report_loads_by_driver, name="report_loads_by_driver"),
    path('report_loads_per_customer/', views.report_loads_per_customer, name="report_loads_per_customer"),
]+ static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

