from django.contrib import admin
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType

from .models import Vehicle, VehicleDriver, Order, Load, Invoice, InvoiceOrder

# Register your models here.


# tramitador_group, created = Group.objects.get_or_create(name='tramitador')
# operador_group, created = Group.objects.get_or_create(name='operador')

# content_type = ContentType.objects.get_for_model(Order)


# # Permisos de tramitador
# permissions = Permission.objects.filter(content_type=content_type)
# tramitador_group.permissions.set(permissions)


# # Permisos de operador
# operador_permissions = Permission.objects.filter(content_type=content_type, codename__in=['add_order', 'edit_order'])
# operador_group.permissions.set(operador_permissions)


class InvoiceOrderInline(admin.TabularInline):
    model = InvoiceOrder
    autocomplete_fields = ['invoice', 'order']


class VehicleAdmin(admin.ModelAdmin):
    search_fields = ['truck_number']


class VehicleDriverAdmin(admin.ModelAdmin):
    list_display = ['vehicle', 'driver', 'active']
    search_fields = ['vehicle__truck_number', 'driver__username']
    autocomplete_fields = ['driver', 'vehicle']


class OrderAdmin(admin.ModelAdmin):
    search_fields = ['customer__name', 'customer__phone_number', 'load__vehicle__truck_number', 'load__driver__username']
    exclude = ['added_by']
    list_display = ['date_order', 'customer', 'pickup_location', 'dropoff_location', 'product', 'get_status_display']
    list_filter = ['active', 'status',]
    date_hierarchy = 'date_order'
    autocomplete_fields = ['customer', 'product', 'pickup_location', 'dropoff_location']

    def save_model(self, request, obj, form, change):
        if getattr(obj, 'added_by', None) is None:
            obj.added_by = request.user
        obj.save()

    #actions = None

    def get_readonly_fields(self, request, obj=None):
        if obj and obj.status == 'completed':
            return self.fields or [f.name for f in self.model._meta.fields]
        return []

    def has_change_permission(self, request, obj=None):
        if obj and obj.status == 'completed':
            return False
        return True

    # def has_delete_permission(self, request, obj=None):
        # if obj and obj.status == 'completed':
            # return False
        # return True


class LoadAdmin(admin.ModelAdmin):
    search_fields = ['order__customer__name', 'order__customer__phone_number', 'vehicle__truck_number', 'driver__username']
    exclude = ['added_by']
    list_display = ['date_added', 'vehicle', 'driver', 'quantity', 'order']
    list_filter = ['order__active', 'order__status',]
    date_hierarchy = 'order__date_order'
    autocomplete_fields = ['order', 'driver', 'vehicle']

    def save_model(self, request, obj, form, change):
        if getattr(obj, 'added_by', None) is None:
            obj.added_by = request.user
        obj.save()

    #actions = None

    def get_readonly_fields(self, request, obj=None):
        if obj and obj.order and obj.order.status == 'completed':
            return self.fields or [f.name for f in self.model._meta.fields]
        return []

    def has_change_permission(self, request, obj=None):
        if obj and obj.order and obj.order.status == 'completed':
            return False
        return True

    # def has_delete_permission(self, request, obj=None):
        # if obj and obj.order.status == 'completed':
            # return False
        # return True


class InvoiceAdmin(admin.ModelAdmin):
    search_fields = ['customer__name', 'customer__phone_number']
    inlines = [InvoiceOrderInline]
    autocomplete_fields = ['customer',]

    #actions = None

    def get_readonly_fields(self, request, obj=None):
        if obj and obj.state == 'sent':
            return self.fields or [f.name for f in self.model._meta.fields]
        return []

    def has_change_permission(self, request, obj=None):
        if obj and obj.state == 'sent':
            return False
        return True

    def has_delete_permission(self, request, obj=None):
        if obj and obj.state == 'sent':
            return False
        return True


admin.site.register(Vehicle, VehicleAdmin)
admin.site.register(VehicleDriver, VehicleDriverAdmin)
admin.site.register(Order, OrderAdmin)
admin.site.register(Load, LoadAdmin)
admin.site.register(Invoice, InvoiceAdmin)
