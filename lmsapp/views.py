from django.shortcuts import render
from django.http import HttpResponseRedirect, FileResponse, HttpResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.core.paginator import Paginator, InvalidPage, EmptyPage, PageNotAnInteger
from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required, user_passes_test
from django.contrib.auth.models import User
from django.db.models import Q, Sum
from django.db.models import Count
from django.utils import timezone
from django.core.files import File
from django.core.files.temp import NamedTemporaryFile
from django.utils.decorators import method_decorator
from django.utils.html import format_html
from django.conf import settings

import datetime
import io
import os
try:
    import zoneinfo
except ImportError:
    #pip install backports.zoneinfo
    from backports import zoneinfo

import xlsxwriter

import datatableview
from datatableview import Datatable, ValuesDatatable, columns, SkipRecord
from datatableview.views import DatatableView, MultipleDatatableView, XEditableDatatableView
from datatableview.views.legacy import LegacyDatatableView
from datatableview import helpers

from common.views import user_admin, user_allowed, user_tramitador, user_operador
from common.models import UserProfile, Customer
from common.models import user_is_driver
from common.lib import image_utils

from .models import Vehicle, VehicleDriver
from .models import Order, Load, Invoice, InvoiceOrder
from .forms import OrderForm, LoadForm, OrderAddTicketForm, OrderFilterForm
from .forms import VehicleForm, search_order_customerForm, search_load_customerForm
from .forms import search_order_vehicleForm
from .forms import InvoiceForm, InvoiceOrderForm, DriverLoadForm

# Create your views here.

@login_required
def index(request):
    status = request.GET.get('status', '')
    now = timezone.now().date()
    customers = Customer.objects.all()
    vehicles = Vehicle.objects.filter(active=True)
    orders = Order.objects.filter(date_order__gte=now)
    loads = Load.objects.filter(date_added__range=(timezone.now().replace(hour=0, minute=0, second=0), timezone.now().replace(hour=23, minute=59, second=59)))
    if status:
        orders = orders.filter(status=status)
    order_pending = orders.filter(status__exact='pending').count()
    order_completed = orders.filter(status__exact='completed').count()

    # Calcular el importe total de todas las órdenes
    totals = orders.aggregate(Sum('total_amount'))['total_amount__sum'] or 0
    try:
        if request.user.userprofile.is_driver():
            totals = request.user.userprofile.driver_earned_today()
            loads = loads.filter(driver=request.user)
    except:
        pass
    loads_pending = loads.filter(Q(ticket__isnull=True) | Q(image='tickets/photos/none.jpg'))
    loads_completed = loads.filter(ticket__isnull=False, order__isnull=False).exclude(image='tickets/photos/none.jpg')

    data = {
        'customers': customers,
        'vehicles': vehicles,
        'orders': orders,
        'order_pending': order_pending,
        'order_completed': order_completed,
        'loads': loads.count(),
        'loads_pending': loads_pending.count(),
        'loads_completed': loads_completed.count(),
        'totals': totals,
    }
    return render(request, "lmsapp/index.html", data)


@login_required
def dashboard(request):
    customers = Customer.objects.all()
    vehicles = Vehicle.objects.filter(active=True)
    orders = Order.objects.all()
    order_pending = Order.objects.filter(status__exact='pending').count()
    order_completed = Order.objects.filter(status__exact='completed').count()
    loads = Load.objects.all()
    load_completed = Load.objects.filter(status__exact='completed').count()

    # Calcular el importe total de todas las órdenes
    totals = 0
    # totals = Order.objects.aggregate(totals=Sum('total_amount'))['totals'] or 0
    for x in orders:
        totals += x.total_amount()

    data = {
        'customers': customers,
        'vehicles': vehicles,
        'orders': orders,
        'order_pending': order_pending,
        'order_completed': order_completed,
        'totals': totals,
        'loads': loads,
        'load_completed': load_completed,
    }
    return render(request, "lmsapp/dashboard.html", data)


@login_required
@user_passes_test(user_is_driver, login_url='/error_permission_required/')
def autoassign_order(request, pk):
    order = get_object_or_404(Order, pk=pk, driver__isnull=True, vehicle__isnull=True)
    order.driver = request.user
    order.save()
    messages.add_message(request, messages.INFO, 'Dricer {} assigned to order'.format(request.user))
    return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))


# # Views for Order
@login_required
@permission_required('lmsapp.add_order', raise_exception=True)
def add_order(request):
    if request.method == 'POST':
        form = OrderForm(request.POST, request.FILES)
        photob64 = request.POST.get('photob64', '')
        if form.is_valid():
            order = form.save(commit=False)
            order.customer = order.dropoff_location
            order.added_by = request.user
            try:
                order.save()
            except:
                #form.fields['product'].required = True
                #form.errors['product'] = ['Could not find a Product to automatically assing to Order. Please, set a product.']
                messages.add_message(request, messages.ERROR, 'Could not find a Product to automatically assing to Order. Please, set a product.')
            form.is_valid()
            if form.is_valid():
                if photob64:
                    photo_file = image_utils.get_image_from_data_url(photob64)[0]
                    order.image = photo_file
                    order.save()
                messages.add_message(request, messages.INFO, 'Order added.')
                return HttpResponseRedirect(reverse('orders_list'))
    else:
        form = OrderForm()

    data = {
        'form':  form,
    }
    return render(request, "lmsapp/add_order.html", data)


@login_required
@permission_required('lmsapp.change_order', raise_exception=True)
def edit_order(request, pk):
    order = get_object_or_404(Order, pk=pk)

    if request.method == 'POST':
        form = OrderForm(request.POST, request.FILES, instance=order)
        photob64 = request.POST.get('photob64', '')
        if form.is_valid():
            order = form.save()
            order.added_for = request.user
            order.save()
            if photob64:
                photo_file = image_utils.get_image_from_data_url(photob64)[0]
                order.image = photo_file
                order.save()
            return HttpResponseRedirect(reverse('orders_list'))
    else:
        form = OrderForm(instance=order)

    data = {
        'order': order,
        'form': form,
    }
    return render(request, "lmsapp/add_order.html", data)


@login_required
@permission_required('lmsapp.add_order', raise_exception=True)
def order_clone(request, pk):
    order = get_object_or_404(Order, pk=pk)

    new_order = Order()
    new_order.date_order = timezone.now()
    new_order.customer = order.customer
    new_order.product = order.product
    new_order.loads = order.loads
    new_order.pickup_location = order.pickup_location
    new_order.dropoff_location = order.dropoff_location
    new_order.added_by = request.user
    new_order.save()
    messages.add_message(request, messages.INFO, 'Order created')

    return HttpResponseRedirect(request.META.get('HTTP_REFERER', reverse('orders_list')))


@login_required
@permission_required('lmsapp.change_order', raise_exception=True)
def order_add_ticket(request, pk):
    order = get_object_or_404(Order, pk=pk)

    if request.method == 'POST':
        form = OrderAddTicketForm(request.POST)
        if form.is_valid():
            photob64 = form.cleaned_data.get('photob64', '')
            if photob64:
                photo_file = image_utils.get_image_from_data_url(photob64)[0]
                order.image = photo_file
                order.save()
                messages.add_message(request, messages.INFO, 'Ticket added to order'.format(request.user))
                return HttpResponseRedirect(reverse('orders_list'))
    else:
        form = OrderAddTicketForm()
    data = {
        'order': order,
        'form': form,
    }
    return render(request, "lmsapp/order_add_ticket.html", data)


@login_required
@permission_required('lmsapp.view_order', raise_exception=True)
def orders_list(request):
    orders_list = Order.objects.all()
    filters = {}
    now = timezone.now()

    form = OrderFilterForm(request.GET)
    form.is_valid()
    q = request.GET.get('q', '')
    status = request.GET.get('status', '')
    date_start = form.cleaned_data.get('date_start')
    if not date_start:
        date_start = now.replace(hour=0, minute=0, second=0)
    if request.user.userprofile and request.user.userprofile.is_driver():
        date_start = timezone.now().date()
    date_end = form.cleaned_data.get('date_end', '')

    if q:
        filters['q'] = q
        orders_list = orders_list.filter(Q(customer__name__contains=q)).distinct()
    if status:
        filters['status'] = status
        orders_list = orders_list.filter(status=status)
    if date_start:
        filters['date_start'] = date_start.strftime('%Y-%m-%d')
        orders_list = orders_list.filter(date_order__gte=date_start)
    if date_end:
        filters['date_end'] = date_end.strftime('%Y-%m-%d')
        orders_list = orders_list.filter(date_order__lte=timezone.datetime(date_end.year, date_end.month, date_end.day, 23, 59, 59))

    # Calcular el importe total de todas las órdenes
    if request.user.userprofile and request.user.userprofile.is_driver():
        totals = Load.objects.filter(driver=request.user, order__in=orders_list).aggregate(Sum('total_driver_amount'))['total_driver_amount__sum'] or 0
        totals_completed = Load.objects.filter(driver=request.user, order__in=orders_list.filter(status='completed')).aggregate(Sum('total_driver_amount'))['total_driver_amount__sum'] or 0
    else:
        totals = orders_list.aggregate(Sum('total_amount'))['total_amount__sum'] or 0
        totals_completed = orders_list.filter(status='completed').aggregate(Sum('total_amount'))['total_amount__sum'] or 0

    paginator = Paginator(orders_list, 10)  # Show 10 consultas per page

    page = request.GET.get('page')
    try:
        orders = paginator.page(page)
    except PageNotAnInteger:
        # If page is not an integer, deliver first page.
        orders = paginator.page(1)
    except EmptyPage:
        # If page is out of range (e.g. 9999), deliver last page of results.
        orders = paginator.page(paginator.num_pages)

    data = {
        'q': q,
        'form': form,
        'orders': orders_list,
        'totals': totals,
        'totals_completed': totals_completed,
        'filters': filters,
    }

    return render(request, "lmsapp/orders_list.html", data)


@login_required
@permission_required('lmsapp.view_order', raise_exception=True)
def order_details(request, pk):
    order = get_object_or_404(Order, pk=pk)

    data = {
        'order': order,
    }
    return render(request, 'lmsapp/order_details.html', data)


@login_required
@permission_required('lmsapp.delete_order', raise_exception=True)
def order_delete(request, pk):
    order = get_object_or_404(Order, pk=pk)
    order.delete()

    return HttpResponseRedirect(reverse('orders_list'))


########################################################################
################                 Loads              ####################
########################################################################


@login_required
@permission_required('lmsapp.add_load', raise_exception=True)
def add_load(request, pk):
    the_order = get_object_or_404(Order, pk=pk)
    if request.method == 'POST':
        if request.user.userprofile and request.user.userprofile.is_driver():
            form = LoadForm(request.POST, request.FILES)
            form.fields['vehicle'].queryset = form.fields['vehicle'].queryset.filter(pk__in=request.user.userprofile.get_actual_vehicles().values_list('vehicle__pk', flat=True))
        else:
            form = LoadForm(request.POST, request.FILES)
            form.fields['vehicle'].queryset = form.fields['vehicle'].queryset.filter(vehicledriver__active=True)
        photob64 = request.POST.get('photob64', '')
        if form.is_valid():
            order = form.save(commit=False)
            order.order = the_order
            order.customer = the_order.customer
            if the_order.product:
                order.product = the_order.product
            order.pickup_location = the_order.pickup_location
            order.dropoff_location = the_order.dropoff_location
            order.added_by = request.user
            order.save()
            if photob64:
                photo_file = image_utils.get_image_from_data_url(photob64)[0]
                order.image = photo_file
                order.save()
            return HttpResponseRedirect(reverse('loads_list'))
    else:
        if request.user.userprofile and request.user.userprofile.is_driver():
            form = LoadForm()
            form.fields['vehicle'].queryset = form.fields['vehicle'].queryset.filter(pk__in=request.user.userprofile.get_actual_vehicles().values_list('vehicle__pk', flat=True))
        else:
            form = LoadForm()
            form.fields['vehicle'].queryset = form.fields['vehicle'].queryset.filter(vehicledriver__active=True)

    data = {
        'form':  form,
    }
    return render(request, "lmsapp/add_load.html", data)


@login_required
@permission_required('lmsapp.add_load', raise_exception=True)
def driver_add_load(request):
    if request.method == 'POST':
        if request.user.userprofile and request.user.userprofile.is_driver():
            form = DriverLoadForm(request.POST, request.FILES)
            form.fields['product'].required = True
            #form.fields['customer'].required = False
            form.fields['pickup_location'].required = True
            form.fields['dropoff_location'].required = True
            form.fields['vehicle'].queryset = form.fields['vehicle'].queryset.filter(pk__in=request.user.userprofile.get_actual_vehicles().values_list('vehicle__pk', flat=True))
        else:
            form = DriverLoadForm(request.POST, request.FILES)
            form.fields['product'].required = True
            #form.fields['customer'].required = False
            form.fields['pickup_location'].required = True
            form.fields['dropoff_location'].required = True
            form.fields['vehicle'].queryset = form.fields['vehicle'].queryset.filter(vehicledriver__active=True)
        photob64 = request.POST.get('photob64', '')
        if form.is_valid():
            #customer = form.cleaned_data['customer']
            customer = form.cleaned_data['dropoff_location']
            pickup_location = form.cleaned_data['pickup_location']
            dropoff_location = form.cleaned_data['dropoff_location']
            product = form.cleaned_data['product']
            now = timezone.now()
            the_order = Order.objects.filter(
                date_order__range=(now.replace(hour=0, minute=0, second=0), now.replace(hour=23, minute=59, second=59)),
                customer = customer,
                pickup_location = pickup_location,
                dropoff_location = dropoff_location,
                product = product,
                status = 'pending'
            ).first()
            if not the_order:
                the_order = Order.objects.filter(
                    date_order__range=(now.replace(hour=0, minute=0, second=0), now.replace(hour=23, minute=59, second=59)),
                    customer = customer,
                    pickup_location = pickup_location,
                    dropoff_location = dropoff_location,
                    status = 'pending'
                ).first()
                if the_order and product:
                    Order.objects.filter(pk=the_order.pk).update(product=product)
            # if not the_order:
                # the_order = Order.objects.create(
                    # customer=customer,
                    # pickup_location = pickup_location,
                    # dropoff_location = dropoff_location,
                    # product = product,
                    # loads = 1,
                    # added_by = request.user
                # )
            order = form.save(commit=False)
            order.order = the_order
            order.added_by = request.user
            order.save()
            if photob64:
                photo_file = image_utils.get_image_from_data_url(photob64)[0]
                order.image = photo_file
                order.save()
            return HttpResponseRedirect(reverse('loads_list'))
    else:
        if request.user.userprofile and request.user.userprofile.is_driver():
            form = DriverLoadForm()
            form.fields['product'].required = True
            #form.fields['customer'].required = False
            form.fields['pickup_location'].required = True
            form.fields['dropoff_location'].required = True
            form.fields['vehicle'].queryset = form.fields['vehicle'].queryset.filter(pk__in=request.user.userprofile.get_actual_vehicles().values_list('vehicle__pk', flat=True))
        else:
            form = DriverLoadForm()
            form = DriverLoadForm()
            form.fields['product'].required = True
            #form.fields['customer'].required = False
            form.fields['pickup_location'].required = True
            form.fields['dropoff_location'].required = True
            form.fields['vehicle'].queryset = form.fields['vehicle'].queryset.filter(vehicledriver__active=True)

    data = {
        'form':  form,
    }
    return render(request, "lmsapp/driver_add_load.html", data)


@login_required
@permission_required('lmsapp.change_load', raise_exception=True)
def edit_load(request, pk):
    order = get_object_or_404(Load, pk=pk)

    if request.method == 'POST':
        form = LoadForm(request.POST, request.FILES, instance=order)
        photob64 = request.POST.get('photob64', '')
        if form.is_valid():
            order = form.save()
            if photob64:
                photo_file = image_utils.get_image_from_data_url(photob64)[0]
                order.image = photo_file
                order.save()
            return HttpResponseRedirect(reverse('loads_list'))
    else:
        form = LoadForm(instance=order)

    data = {
        'order': order,
        'form': form,
    }
    return render(request, "lmsapp/add_load.html", data)


@login_required
@permission_required('lmsapp.change_load', raise_exception=True)
def load_add_ticket(request, pk):
    order = get_object_or_404(Load, pk=pk)

    if request.method == 'POST':
        form = OrderAddTicketForm(request.POST)
        if form.is_valid():
            photob64 = form.cleaned_data.get('photob64', '')
            if photob64:
                photo_file = image_utils.get_image_from_data_url(photob64)[0]
                order.image = photo_file
                order.save()
                messages.add_message(request, messages.INFO, 'Ticket added to load')
                return HttpResponseRedirect(reverse('loads_list'))
    else:
        form = OrderAddTicketForm()
    data = {
        'order': order,
        'form': form,
    }
    return render(request, "lmsapp/load_add_ticket.html", data)


@login_required
@permission_required('lmsapp.view_load', raise_exception=True)
def loads_list(request):
    orders_list = Load.objects.all().order_by('-date_added')
    filters = {}
    now = timezone.now()
    if request.user.userprofile and request.user.userprofile.is_driver():
        orders_list = orders_list.filter(driver=request.user)

    form = OrderFilterForm(request.GET)
    form.is_valid()
    q = request.GET.get('q', '')
    customer = request.GET.get('customer', '')
    driver = request.GET.get('driver', '')
    status = request.GET.get('status', '')
    date_start = form.cleaned_data.get('date_start')
    date_end = form.cleaned_data.get('date_end', '')
    if not date_start:
        date_start = now.replace(hour=0, minute=0, second=0)

    if q:
        filters['q'] = q
        orders_list = orders_list.filter(
            Q(order__pickup_location__name__icontains=q) | 
            Q(pickup_location__name__icontains=q) | 
            Q(order__dropoff_location__name__icontains=q) | 
            Q(dropoff_location__name__icontains=q)
        ).distinct()
    if customer:
        filters['customer'] = customer
        orders_list = orders_list.filter(customer=customer)
    if driver:
        filters['driver'] = driver
        orders_list = orders_list.filter(driver=driver)
    if status:
        filters['status'] = status
        orders_list = orders_list.filter(order__status=status)
    if date_start:
        filters['date_start'] = date_start.strftime('%Y-%m-%d')
        orders_list = orders_list.filter(date_added__gte=date_start)
    if date_end:
        filters['date_end'] = date_end.strftime('%Y-%m-%d')
        orders_list = orders_list.filter(date_added__lte=timezone.datetime(date_end.year, date_end.month, date_end.day, 23, 59, 59))

    # Calcular el importe total de todas las órdenes
    if request.user.userprofile and request.user.userprofile.is_driver():
        totals = orders_list.aggregate(Sum('total_driver_amount'))['total_driver_amount__sum'] or 0
        totals_completed = orders_list.filter(ticket__isnull=False).exclude(Q(ticket='') | Q(image='tickets/photos/none.jpg')).aggregate(Sum('total_driver_amount'))['total_driver_amount__sum'] or 0
    else:
        totals = orders_list.aggregate(Sum('total_amount'))['total_amount__sum'] or 0
        totals_completed = orders_list.filter(ticket__isnull=False).exclude(Q(ticket='') | Q(image='tickets/photos/none.jpg')).aggregate(Sum('total_amount'))['total_amount__sum'] or 0

    paginator = Paginator(orders_list, 10)  # Show 10 consultas per page

    page = request.GET.get('page')
    try:
        orders = paginator.page(page)
    except PageNotAnInteger:
        # If page is not an integer, deliver first page.
        orders = paginator.page(1)
    except EmptyPage:
        # If page is out of range (e.g. 9999), deliver last page of results.
        orders = paginator.page(paginator.num_pages)

    data = {
        'q': q,
        'form': form,
        'orders': orders_list,
        'totals': totals,
        'totals_completed': totals_completed,
        'filters': filters,
        'date_start': date_start,
        'date_end': date_end,
    }

    return render(request, "lmsapp/loads_list.html", data)


@login_required
@permission_required('lmsapp.view_load', raise_exception=True)
def load_details(request, pk):
    order = get_object_or_404(Load, pk=pk)

    data = {
        'order': order,
    }
    return render(request, 'lmsapp/load_details.html', data)


@login_required
@permission_required('lmsapp.delete_load', raise_exception=True)
def load_delete(request, pk):
    if request.user.userprofile and request.user.userprofile.is_driver():
        order = get_object_or_404(Load, pk=pk, added_by=request.user)
    order = get_object_or_404(Load, pk=pk)

    the_order = order.order
    order.delete()
    if the_order:
        the_order.save()
    return HttpResponseRedirect(reverse('loads_list'))


########################################################################
################                Invoice             ####################
########################################################################


@method_decorator(login_required, name='dispatch')
@method_decorator(permission_required('lmsapp.view_invoice', login_url='/error_permission_required/'), name='dispatch')
class InvoiceDatatableView(DatatableView):
    model = Invoice

    # def get_queryset(self):
        # qs = super().get_queryset()
        # return qs.order_by('level', 'name')

    class datatable_class(Datatable):
        get_absolute_url = columns.TextColumn("Acciones", sources=None, processor="get_absolute_url_fn")

        class Meta:
            model = Invoice
            columns = ['id', 'code', 'number', 'state', 'date', 'date_start', 'date_end', 'customer', 'total_amount', 'date_added']
            search_fields = ['number', 'customer__name']
            hidden_columns = ['id', 'code']
            structure_template = "datatableview/bootstrap_structure.html"
            request_method = "POST"
            ordering = None
            processors = {'date_added': 'process_date'}

        def get_absolute_url_fn(self, instance, **kwargs):
            return format_html('<a href="{}" class="btn btn-xs btn-block btn-success"><i class="zmdi zmdi-eye"></i> Details</a>', instance.get_absolute_url())

        def process_date(self, instance, **kwargs):
            return instance.date_added.astimezone(tz=zoneinfo.ZoneInfo(settings.TIME_ZONE)).strftime('%Y-%m-%d %H:%M:%S')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['now'] = timezone.now()
        context['MEDIA_URL'] = settings.MEDIA_URL
        return context


@login_required
@permission_required('lmsapp.add_invoice', raise_exception=True)
def add_invoice(request):
    if request.method == 'POST':
        form = InvoiceForm(request.POST)
        form.fields['customer'].queryset = form.fields['customer'].queryset.filter(pk__in=Order.objects.filter(invoiceorder__isnull=True).values_list('customer__pk', flat=True).distinct())
        if form.is_valid():
            invoice = form.save()
            date_start = timezone.now().replace(
                year=invoice.date_start.year,
                month=invoice.date_start.month,
                day=invoice.date_start.day,
                hour=0,
                minute=0,
                second=0
            )
            date_end = timezone.now().replace(
                year=invoice.date_end.year,
                month=invoice.date_end.month,
                day=invoice.date_end.day,
                hour=23,
                minute=59,
                second=59
            )
            #for order in Order.objects.filter(status='completed', customer=invoice.customer, invoiceorder__isnull=True, date_order__range=(invoice.date_start, invoice.date_end)):
            for order in Order.objects.filter(customer=invoice.customer, invoiceorder__isnull=True, date_order__range=(date_start, date_end)):
                io, created = InvoiceOrder.objects.get_or_create(invoice=invoice, order=order)
            invoice.save()
            messages.add_message(request, messages.INFO, 'Invoice added for customer {} with all competed orders in date range.'.format(invoice.customer))
            return HttpResponseRedirect(reverse('invoice_list'))
        else:
            messages.add_message(request, messages.ERROR, 'Please, correct errors')
    else:
        form = InvoiceForm()
        #form.fields['customer'].queryset = form.fields['customer'].queryset.filter(pk__in=Order.objects.filter(status='completed', invoiceorder__isnull=True).values_list('customer__pk', flat=True).distinct())
        form.fields['customer'].queryset = form.fields['customer'].queryset.filter(pk__in=Order.objects.filter(invoiceorder__isnull=True).values_list('customer__pk', flat=True).distinct())

    data = {
        'form':  form,
    }
    return render(request, "lmsapp/add_invoice.html", data)


@login_required
@permission_required('lmsapp.add_invoice', raise_exception=True)
def invoice_details(request, pk):
    invoice = get_object_or_404(Invoice, pk=pk)

    data = {
        'invoice': invoice,
    }
    return render(request, 'lmsapp/invoice_details.html', data)


@login_required
@permission_required('lmsapp.view_invoice', raise_exception=True)
def invoice_show_barcode(request, pk):
    invoice = get_object_or_404(Invoice, pk=pk)
    
    barcode = open(invoice.get_barcode(), 'rb')
    
    return FileResponse(barcode)


@login_required
@permission_required('lmsapp.view_invoice', raise_exception=True)
def invoice_to_excel(request, pk):
    invoice = get_object_or_404(Invoice, pk=pk)
    output = io.BytesIO()
    workbook = xlsxwriter.Workbook(output)
    worksheet = workbook.add_worksheet("Invoice")
    header = workbook.add_format({"bold": True})
    #header = workbook.add_format({"bold": True, "align": "center"})
    merge_format = workbook.add_format(
        {
            "bold": 1,
            "border": 1,
            "align": "center",
            "valign": "vcenter",
            #"fg_color": "yellow",
        }
    )
    merge_format_total = workbook.add_format(
        {
            "bold": 1,
            "border": 1,
            "align": "right",
            "valign": "vcenter",
            #"fg_color": "yellow",
        }
    )
    
    worksheet.merge_range("A1:B6", "", merge_format)
    worksheet.set_column("A:B", 8)
    worksheet.insert_image("A1", os.path.join(settings.STATIC_ROOT_PATH, 'img/logosquare.png'), {"x_scale": 0.25, "y_scale": 0.25})
    worksheet.merge_range("C1:H1", "DOUBLE O CONTRACTING LLC", merge_format)
    worksheet.merge_range("C2:H2", "109 Birch St, Old Bridge, NJ 08857", merge_format)
    worksheet.merge_range("C3:H3", "Date: {}".format(invoice.date.strftime("%Y-%m-%d")), merge_format)
    worksheet.merge_range("C4:H4", "INVOICE SHEET: {}".format(invoice.number), merge_format)
    worksheet.merge_range("C5:H5", "CLIENT: {}".format(invoice.customer), merge_format)
    worksheet.merge_range(
        "C6:H6",
        "LOADS: {} FROM: {} TO: {}".format(
            invoice.get_loads().count(),
            invoice.date_start.strftime("%Y-%m-%d"),
            invoice.date_end.strftime("%Y-%m-%d")
        ),
        merge_format
    )
    worksheet.autofit()

    worksheet_data = workbook.add_worksheet("Loads")
    worksheet_data.write("A1", "TRUCK", merge_format)
    worksheet_data.write("B1", "DATE", merge_format)
    worksheet_data.write("C1", "TICKET", merge_format)
    worksheet_data.write("D1", "ORIGIN", merge_format)
    worksheet_data.write("E1", "DESTINATION", merge_format)
    worksheet_data.write("F1", "PRODUCT", merge_format)
    worksheet_data.write("G1", "QUANTITY", merge_format)
    worksheet_data.write("H1", "RATE", merge_format)
    worksheet_data.write("I1", "AMOUNT", merge_format)
    row = 2
    for load in invoice.get_loads():
        worksheet_data.write("A{}".format(row), load.vehicle.truck_number)
        worksheet_data.write("B{}".format(row), load.order.date_order.strftime("%Y-%m-%d"))
        worksheet_data.write("C{}".format(row), load.ticket or '-')
        worksheet_data.write("D{}".format(row), load.order.pickup_location.name)
        worksheet_data.write("E{}".format(row), load.order.dropoff_location.name)
        worksheet_data.write("F{}".format(row), load.order.product.product)
        worksheet_data.write("G{}".format(row), load.quantity)
        worksheet_data.write("H{}".format(row), load.order.price)
        worksheet_data.write("I{}".format(row), load.total_amount)
        row += 1
    worksheet_data.merge_range("A{}:H{}".format(row, row), "TOTAL: $", merge_format_total)
    worksheet_data.write("I{}".format(row), invoice.total_amount, merge_format)
    worksheet_data.autofit()

    workbook.close()
    output.seek(0)
    filename = "invoice-{}.xlsx".format(invoice.date.strftime("%Y-%m-%d"))
    response = HttpResponse(
        output,
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    response["Content-Disposition"] = "attachment; filename=%s" % filename

    return response


########################################################################
################                Reports             ####################
########################################################################


@login_required
@permission_required('lmsapp.view_load', raise_exception=True)
def report_loads_by_driver(request):
    loads_list = Load.objects.all()
    form = search_order_vehicleForm(request.GET)
    if form.is_valid():
        drv = form.cleaned_data.get('driver', None)
        if drv:
            loads_list = loads_list.filter(driver=drv)
        start_date = form.cleaned_data.get('start_date', '')
        if start_date:
            loads_list = loads_list.filter(date_added__gte=start_date)
        end_date = form.cleaned_data.get('end_date', '')
        if end_date:
            loads_list = loads_list.filter(date_added__lte=timezone.datetime(end_date.year, end_date.month, end_date.day, 23, 59, 59))

    drivers = User.objects.filter(assigned_loads__pk__in=loads_list.values_list('pk', flat=True)).distinct()
    #drivers = User.objects.all()
    for driver in drivers:
        driver.total_orders = loads_list.filter(driver=driver).distinct().count()

    data = {
        'drivers': drivers,
        'form': form,
    }
    return render(request, 'lmsapp/report_loads_by_driver.html', data)


@login_required
@permission_required('lmsapp.view_order', raise_exception=True)
def report_orders_per_customer(request):
    customers = Customer.objects.all().distinct()

    form = search_order_customerForm(request.GET)
    form.is_valid()
    initial_date = form.cleaned_data.get('initial_date')
    final_date = form.cleaned_data.get('final_date')
    if not initial_date:
        initial_date = timezone.now().replace(hour=0, minute=0, second=0)
    if not final_date:
        final_date = timezone.now().replace(hour=23, minute=59, second=59)
    customer = form.cleaned_data.get('customer')

    orders = Order.objects.filter(date_order__range=(initial_date, final_date)).order_by('date_order').distinct()

    customers = Customer.objects.annotate(total_orders=Count('customer'))

    data = {
        'orders': orders,
        'customers': customers,
        'form': form,
        'cust': customer,
        'initial_date': initial_date,
        'final_date': final_date
    }
    return render(request, 'lmsapp/report_orders_per_customer.html', data)


@login_required
@permission_required('lmsapp.view_order', raise_exception=True)
def report_loads_per_customer(request):
    loads_list = Load.objects.all()
    form = search_load_customerForm(request.GET)
    form.is_valid()
    q = form.cleaned_data.get('q')
    product = form.cleaned_data.get('product')
    driver = form.cleaned_data.get('driver')
    date_start = form.cleaned_data.get('date_start')
    if request.user.userprofile and request.user.userprofile.is_driver():
        date_start = timezone.now().date()
        loads_list = loads_list.filter(driver=request.user)
    date_end = form.cleaned_data.get('date_end', '')
    filters = {}

    if q:
        filters['q'] = q
        loads_list = loads_list.filter(Q(order__customer__name__contains=q)).distinct()
    if product:
        filters['product'] = product.pk
        loads_list = loads_list.filter(Q(order__product=product) | Q(product=product)).distinct()
    if driver:
        filters['driver'] = driver.pk
        loads_list = loads_list.filter(driver=driver).distinct()
    if date_start:
        filters['date_start'] = date_start.strftime('%Y-%m-%d')
        loads_list = loads_list.filter(date_added__gte=date_start)
    if date_end:
        filters['date_end'] = date_end.strftime('%Y-%m-%d')
        loads_list = loads_list.filter(date_added__lte=timezone.datetime(date_end.year, date_end.month, date_end.day, 23, 59, 59))

    customers = Customer.objects.filter(pk__in=loads_list.values_list('order__customer__pk', flat=True))

    for customer in customers:
        total_loads = loads_list.filter(order__customer=customer).distinct().count()
        customer.total_loads = total_loads

    data = {
        'customers': customers,
        'form': form,
        'q': q,
    }
    return render(request, 'lmsapp/report_loads_per_customer.html', data)
