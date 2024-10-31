from django.db import models
from django.db.models import Q, Sum
from django.db.models.signals import post_save
from django.contrib.auth.models import User, Group
from django.utils import timezone
from django.conf import settings
from django.dispatch import receiver
from django.urls import reverse
from django.utils.html import format_html
from django.core.exceptions import ValidationError

from simple_history.models import HistoricalRecords
from simple_history import register
from auditlog.models import AuditlogHistoryField
from auditlog.registry import auditlog
from rest_framework.authtoken.models import Token

import uuid

import barcode
from barcode.writer import ImageWriter
import qrcode

# Create your models here.

register(User, app=__package__)
register(Group, app=__package__)
register(Token, app=__package__)

COLORS = (
    ('primary', 'Azul claro'),
    ('secondary', 'Gris'),
    ('success', 'Verde'),
    ('danger', 'Rojo'),
    ('warning', 'Naranja'),
    ('info', 'Verde azul'),
    ('light', 'Sin color'),
    ('dark', 'Gris oscuro'),
)


def user_is_driver(user):
    return user.groups.filter(name='DRIVER').count()


class UserProfile(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    history = AuditlogHistoryField()
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    phone_number = models.CharField(u"Phone number", max_length=12, unique=True, null=True, blank=True)
    photo = models.ImageField(u"Photo", upload_to='users/photos/', blank=True, null=True, default='users/photo/none.jpg')
    show_earned = models.BooleanField(default=False)
    date_added = models.DateTimeField("Date added", auto_now_add=True, blank=True, null=True)

    def __str__(self):
        return self.user.username
    
    class Meta:
        verbose_name = "User Profile"
        verbose_name_plural = "User Profile"
    
    def datos_pendientes(self):
        if not self.user.first_name or not self.user.last_name:
            return True
        return False
    
    def nombre_completo(self):
        result = self.user.username
        if self.user.first_name:
            result = self.user.first_name
        if self.user.last_name:
            result += u' {}'.format(self.user.last_name)
        return result
    
    def get_barcode(self):
        datos = '{} - {} - {}'.format(self.user.pk, self.nombre_completo(), self.phone_number)
        #datos = u'N:{}\nA:{}\nCI:{}\nURL:{}\n'.format(self.nombre, self.apellidos(), self.ci, reverse('persona_details', args=[self.pk]))
        if settings.CODE_TYPE == 'bar':
            writer = ImageWriter()
            #writer.set_options(module_height=1)
            name = barcode.generate('code128', datos, output='%s/codes/%s.png' % (settings.MEDIA_ROOT, self.user.pk), writer=writer)
        else:
            codigo_qr = qrcode.make(datos)
            codigo_qr.save('%s/codes/%s.png' % (settings.MEDIA_ROOT, self.pk))
            name = '%s/codes/%s.png' % (settings.MEDIA_ROOT, self.pk)
        return name

    def get_barcode_url(self):
        barcode = reverse('show_barcode', args=[self.pk])
        return format_html('<a href="{}" target="_blank"><img src="{}" class="img-fluid" /></a>', barcode, barcode)

    '''NECESITO Crear los permisos de usuario, en este casos erian superadmin, tramitador y operador'''

    def get_user_roles(self):
        return self.user.groups.all()

    def get_user_roles_labels(self):
        return self.get_user_roles().values_list('name', flat=True)

    def is_operator(self):
        return 'OPERATOR' in self.get_user_roles_labels() or self.user.is_superuser

    def is_driver(self):
        return 'DRIVER' in self.get_user_roles_labels()

    def get_actual_vehicles(self):
        return self.user.vehicledriver_set.filter(active=True)

    def driver_earned_today(self):
        now = timezone.now().date()
        return self.user.assigned_loads.filter(date_added__gte=now).aggregate(Sum('total_driver_amount'))['total_driver_amount__sum'] or 0

auditlog.register(UserProfile)


def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)
        try:
            grupo = Group.objects.get(name='operador')
            instance.groups.add(grupo)
        except:
            pass

post_save.connect(create_user_profile, sender=User)


class UnitMeasurement(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    unitmeasurement = models.CharField("Unit of Measurement", max_length=200, unique=True)
    date_added = models.DateTimeField("Date added", auto_now_add=True, blank=True, null=True)

    def __str__(self):
        return self.unitmeasurement

    class Meta:
        verbose_name = "Unit Measurement"
        verbose_name_plural = "Units of Measurement"


class Product(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    active = models.BooleanField(default=True)
    product = models.CharField("Product", max_length=200, unique=True)
    unitmeasurement = models.ForeignKey(UnitMeasurement, on_delete=models.CASCADE)
    date_added = models.DateTimeField("Date added", auto_now_add=True, blank=True, null=True)

    def __str__(self):
        return self.product

    class Meta:
        verbose_name = "Product"
        verbose_name_plural = "Products"
        ordering = ['product']


class Customer(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    active = models.BooleanField(default=True)
    name = models.CharField("Name", max_length=200, unique=True)
    phone_number = models.CharField("Phone Number", max_length=15, blank=True, null=True)
    address = models.CharField("Address", max_length=150, blank=True, null=True)
    date_added = models.DateTimeField("Date added", auto_now_add=True, blank=True, null=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']
        get_latest_by = 'date_added'
        verbose_name = "Customer"
        verbose_name_plural = "Customers"

    def get_absolute_url(self):
        return reverse('edit_customer', args=[self.pk])

    def active_orders(self):
        return self.order_set.filter(activo=True)

    def cancelled_orders(self):
        return self.order_set.filter(status='cancelled')


class OriginDestinationRate(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    origin = models.ForeignKey(Customer, on_delete=models.CASCADE, verbose_name="Pickup Location", related_name='origin_rate')
    destination = models.ForeignKey(Customer, on_delete=models.CASCADE, verbose_name="Dropoff Location", related_name='destination_rate')
    rate = models.DecimalField("Rate", max_digits=19, decimal_places=2)
    date_added = models.DateTimeField("Date added", auto_now_add=True, blank=True, null=True)

    def __str__(self):
        return '{} - {}: ${}'.format(self.origin, self.destination, self.rate)

    class Meta:
        ordering = ['origin__name', 'destination__name']
        verbose_name = "Origin/Destination Rate"
        verbose_name_plural = "Origins/Destinations Rates"
        unique_together = ['origin', 'destination']

    def clean(self):
        if OriginDestinationRate.objects.filter(origin=self.origin, destination=self.destination).exclude(pk=self.pk):
            raise ValidationError('There is already an Origin/Destination Rate with this Origin adn this Destination.')
