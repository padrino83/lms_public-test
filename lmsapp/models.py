from django.db import models
from django.db.models import Q, Sum
from django.db.models.signals import pre_delete, post_delete
from django.contrib.auth.models import User, Group
from django.utils import timezone
from django.utils.html import format_html
from django.urls import reverse
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator
from django.conf import settings

import uuid
try:
    import zoneinfo
except ImportError:
    #pip install backports.zoneinfo
    from backports import zoneinfo

from decimal import Decimal

import barcode
from barcode.writer import ImageWriter
import qrcode

from common.models import UnitMeasurement, Product, Customer, OriginDestinationRate

# Create your models here.


STATUS = (
    ('pending', 'Pending'),
    ('completed', 'Completed'),
    ('cancelled', 'Cancelled'),
)

INVOICE_STATE_CHOICES = (('deleted', 'Deleted'), ('pending', 'Pending'), ('sent', 'Sent'))


def get_date():
    return timezone.now().astimezone(tz=zoneinfo.ZoneInfo(settings.TIME_ZONE)).date()


class Vehicle(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    active = models.BooleanField(default=True)
    truck_number = models.CharField("Truck Number", max_length=10)
    date_added = models.DateTimeField("Date added", auto_now_add=True, blank=True, null=True)

    def __str__(self):
        result = self.truck_number
        for vd in self.vehicledriver_set.filter(active=True):
            result = '{} - {}'.format(result, vd.driver.get_full_name())
        return result

    class Meta:
        verbose_name = "Vehicle"
        verbose_name_plural = "Vehicles"
        ordering = ['truck_number']


class VehicleDriver(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    active = models.BooleanField(default=True)
    driver = models.ForeignKey(User, on_delete=models.CASCADE)
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE)
    date_added = models.DateTimeField("Date added", auto_now_add=True, blank=True, null=True)

    def __str__(self):
        return '{} - {}'.format(self.vehicle, self.driver)

    class Meta:
        verbose_name = "Vehicle / Driver"
        verbose_name_plural = "Vehicles / Drivers"
        ordering = ['-date_added']
        unique_together = ['driver', 'vehicle']

    def save(self, *args, **kwargs):
        if self.active:
            VehicleDriver.objects.filter(driver=self.driver).exclude(pk=self.pk).update(active=False)
            VehicleDriver.objects.filter(vehicle=self.vehicle).exclude(pk=self.pk).update(active=False)
        super().save(*args, **kwargs)


class Order(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    active = models.BooleanField(default=True)
    status = models.CharField("Status", max_length=20, choices=STATUS, default='pending')
    date_order = models.DateTimeField("Date Order", default=timezone.now)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, verbose_name="Customer", related_name='customer')
    product = models.ForeignKey(Product, null=True, blank=True, on_delete=models.SET_NULL)
    loads = models.PositiveSmallIntegerField('Loads')
    price = models.DecimalField("Rate", default=0.0, max_digits=19, decimal_places=2, null=True, blank=True)
    total_amount = models.DecimalField("Total Amount", default=0.0, max_digits=19, decimal_places=2)
    pickup_location = models.ForeignKey(Customer, on_delete=models.CASCADE, verbose_name="Pickup Location", related_name='pickup')
    dropoff_location = models.ForeignKey(Customer, on_delete=models.CASCADE, verbose_name="Dropoff Location", related_name='dropoff')
    image = models.ImageField(upload_to='tickets/photos/', blank=True, null=True, default='tickets/photos/none.jpg')
    added_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.CASCADE)
    date_added = models.DateTimeField("Date added", auto_now_add=True, blank=True, null=True)

    def __str__(self):
        return '{}: {} to {}'.format(self.date_order.strftime('%Y-%m-%d %H:%M'), self.pickup_location, self.dropoff_location)

    class Meta:
        verbose_name = "Order"
        verbose_name_plural = "Orders"
        ordering = ['-date_order']

    def clean(self):
        if not self.price and self.status == 'completed':
            raise ValidationError('The Order can not be marked as COMPLETED without a RATE!.')

    def save(self, *args, **kwargs):
        if not self.customer and self.dropoff_location:
            self.customer = self.dropoff_location
        if not self.price:
            price = OriginDestinationRate.objects.filter(origin=self.pickup_location, destination=self.dropoff_location).first()
            if price:
                self.price = price.rate
        super().save(*args, **kwargs)
        order_date = timezone.now().replace(year=self.date_order.year, month=self.date_order.month, day=self.date_order.day)
        if self.loads and self.loads > self.load_set.all().count():
            if self.product:
                loads = Load.objects.filter(
                    order__isnull=True,
                    date_added__range=(order_date.replace(hour=0, minute=0, second=0), order_date.replace(hour=23, minute=59,second=59)),
                    customer=self.customer,
                    product=self.product,
                    pickup_location=self.pickup_location,
                    dropoff_location=self.dropoff_location
                )
            else:
                loads = Load.objects.filter(
                    order__isnull=True,
                    date_added__range=(order_date.replace(hour=0, minute=0, second=0), order_date.replace(hour=23, minute=59,second=59)),
                    customer=self.customer,
                    #product=self.product,
                    pickup_location=self.pickup_location,
                    dropoff_location=self.dropoff_location
                )
                if loads.count():
                    self.product = loads.first().product
                loads = Load.objects.filter(
                    order__isnull=True,
                    date_added__range=(order_date.replace(hour=0, minute=0, second=0), order_date.replace(hour=23, minute=59,second=59)),
                    customer=self.customer,
                    product=self.product,
                    pickup_location=self.pickup_location,
                    dropoff_location=self.dropoff_location
                )
            for l in loads[:self.loads]:
                Load.objects.filter(pk=l.pk).update(order=self)
        for load in self.load_set.all():
            load.save()
        self.total_amount = self.get_total_amount()
        if self.price > 0 and self.loads <= self.load_set.all().count():
            self.status = 'completed'
        else:
            self.status = 'pending'
        super().save(*args, **kwargs)

    def get_total_amount(self):
        return (self.price or 0) * (self.load_set.all().aggregate(Sum('quantity'))['quantity__sum'] or 0)

    def can_get_loads(self):
        return self.load_set.all().count() == 0 or self.loads > self.load_set.all().count()

    def get_total_quantity(self):
        return self.load_set.all().aggregate(Sum('quantity'))['quantity__sum']


def delete_order(sender, instance, **kwargs):
    instance.load_set.all().update(total_amount=0, total_driver_amount=0)

pre_delete.connect(delete_order, sender=Order)


class Load(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    customer = models.ForeignKey(Customer, null=True, blank=True, on_delete=models.SET_NULL, verbose_name="Customer", related_name='load_customer')
    product = models.ForeignKey(Product, null=True, blank=True, on_delete=models.SET_NULL)
    pickup_location = models.ForeignKey(Customer, null=True, blank=True, on_delete=models.SET_NULL, verbose_name="Pickup Location", related_name='load_pickup')
    dropoff_location = models.ForeignKey(Customer, null=True, blank=True, on_delete=models.SET_NULL, verbose_name="Dropoff Location", related_name='load_dropoff')
    order = models.ForeignKey(Order, null=True, blank=True, on_delete=models.SET_NULL)
    ticket = models.CharField('Ticket', max_length=20, null=True, blank=True)
    vehicle = models.ForeignKey(Vehicle, null=True, blank=False, on_delete=models.SET_NULL)
    driver = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name="assigned_loads")
    quantity = models.DecimalField("Tons", max_digits=19, decimal_places=2)#, validators=[MaxValueValidator(30)])
    total_amount = models.DecimalField("Total Amount", default=0.0, max_digits=19, decimal_places=2)
    total_driver_amount = models.DecimalField("Total Driver Amount", default=0.0, max_digits=19, decimal_places=2)
    image = models.ImageField(upload_to='tickets/photos/', blank=True, null=True, default='tickets/photos/none.jpg')
    added_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.CASCADE)
    date_added = models.DateTimeField("Date added", auto_now_add=True, blank=True, null=True)

    class Meta:
        verbose_name = "Load"
        verbose_name_plural = "Loads"
        ordering = ['-date_added']

    def __str__(self):
        return '{}: {}'.format(self.vehicle, self.date_added)

    def clean(self):
        if self.vehicle and not self.vehicle.active:
            raise ValidationError('Cannot create orders for inactive vehicles.')
        #if self.quantity > 30:
        #    raise ValidationError('The quantity cannot be greater than 30.')

    def save(self, *args, **kwargs):
        if not self.customer and self.dropoff_location:
            self.customer = self.dropoff_location
        if not self.driver and self.vehicle:
            driver = User.objects.filter(pk__in=[self.vehicle.vehicledriver_set.filter(active=True).values_list('driver__pk', flat=True)]).first()
            self.driver = driver
        if self.driver and not self.vehicle:
            vehicle = Vehicle.objects.filter(pk__in=[str(pk) for pk in self.driver.vehicledriver_set.filter(active=True).values_list('vehicle__pk', flat=True)]).first()
            self.vehicle = vehicle
        if self.order:
            self.total_amount = self.get_total_amount()
        else:
            self.total_amount = 0
        try:
            self.total_driver_amount = (self.total_amount * 30) / 100
        except:
            pass
        if self.order:
            if not self.customer:
                self.customer = self.order.customer
            if not self.product:
                self.product = self.order.product
            if not self.pickup_location:
                self.pickup_location = self.order.pickup_location
            if not self.dropoff_location:
                self.dropoff_location = self.order.dropoff_location
        super().save(*args, **kwargs)
        if self.order:
            Order.objects.filter(pk=self.order.pk).update(total_amount=self.order.get_total_amount())

    def get_total_amount(self):
        if self.order:
            return Decimal(self.order.price) * Decimal(self.quantity)
        return 0

    def driver_percent(self):
        try:
            return (self.total_amount() * 30) / 100
        except:
            pass
        return 0.0

    def get_status(self):
        if self.order and self.ticket and self.total_amount and self.image and self.image != 'tickets/photos/none.jpg':
            return 'Completed'
        return 'Pending'

def delete_load(sender, instance, **kwargs):
    if instance.order:
        Order.objects.filter(pk=instance.order.pk).update(total_amount=instance.order.get_total_amount())

post_delete.connect(delete_load, sender=Load)


class Invoice(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField("Code", max_length=120, null=True, blank=True, default=uuid.uuid4)
    number = models.CharField("Invoice Number", max_length=120, null=True, blank=True)
    state = models.CharField("STATE", max_length=20, choices=INVOICE_STATE_CHOICES, default='pending')
    date = models.DateField("Date", blank=False, null=True, default=get_date, help_text='Date of invoice.')
    date_start = models.DateField("Date start", null=True, blank=False, help_text='Starting Date of invoice orders.')
    date_end = models.DateField("Date end", null=True, blank=False, help_text='End Date of invoice orders.')
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, verbose_name="Customer")
    total_amount = models.DecimalField("Total Amount", default=0.0, max_digits=19, decimal_places=2)
    date_added = models.DateTimeField("Date added", auto_now_add=True, blank=True, null=True)

    # history = HistoricalRecords()

    class Meta:
        verbose_name = "Invoice"
        verbose_name_plural = "Invoices"
        ordering = ['-date_added']

    def __str__(self):
        return '{}: Number: {} | Code: {} [{}]'.format(self.customer, self.number or '-', self.code or '-', self.date)

    def save(self, *args, **kwargs):
        if not self.code:
            self.code = str(uuid.uuid4())
        super().save(*args, **kwargs)
        Invoice.objects.filter(pk=str(self.pk)).update(total_amount=self.invoiceorder_set.all().aggregate(Sum('order__total_amount'))['order__total_amount__sum'] or 0)

    def get_absolute_url(self):
        return reverse('invoice_details', args=[str(self.pk)])

    def get_absolute_edit_url(self):
        return reverse('invoice_edit', args=[str(self.pk)])

    def get_barcode(self):
        datos = u'{}'.format(self.code)
        if settings.CODE_TYPE == 'bar':
            writer = ImageWriter()
            # writer.set_options(module_height=1)
            name = barcode.generate('code128', datos, output='%s/codes/invoice-%s' % (settings.MEDIA_ROOT, str(self.pk)), writer=writer)
        else:
            codigo_qr = qrcode.make(datos)
            codigo_qr.save('%s/codes/invoice-%s.png' % (settings.MEDIA_ROOT, str(self.pk)))
            name = '%s/codes/invoice-%s.png' % (settings.MEDIA_ROOT, str(self.pk))
        return name

    def get_barcode_url(self):
        barcode = reverse('invoice_show_barcode', args=[str(self.pk)])
        return format_html('<a href="{}" target="_blank"><img src="{}" class="img-responsive" /></a>', barcode, barcode)

    def get_loads(self):
        return Load.objects.filter(order__pk__in=self.invoiceorder_set.all().values_list('order__pk', flat=True)).distinct()

class InvoiceOrder(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE)
    order = models.ForeignKey(Order, on_delete=models.CASCADE)#, limit_choices_to={"status": 'completed', 'invoiceorder__isnull': True})
    date_added = models.DateTimeField("Date added", auto_now_add=True, blank=True, null=True)

    class Meta:
        verbose_name = "Invoice/Order"
        verbose_name_plural = "Invoices/Orders"

    def __str__(self):
        return '{}: {} - {}'.format(self.date_added, self.invoice, self.order)

    def clean(self):
        if self.invoice.customer != self.order.customer:
            raise ValidationError("Invoice Customer and Order Customer are not the same!")
        # if self.order.status != 'completed':
            # raise ValidationError("Order not competed!")
        if self.order.invoiceorder_set.all().exclude(pk=self.pk).count():
            raise ValidationError("Order has been included on other Invice.")
