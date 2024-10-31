from django.contrib import admin
from django.http import HttpResponse
from django.core import serializers

from simple_history import register
from simple_history.admin import SimpleHistoryAdmin

from .models import UserProfile, UnitMeasurement, Product, Customer, OriginDestinationRate

# Register your models here.

def export_as_json(modeladmin, request, queryset):
    """Exportar datos en formato json"""
    response = HttpResponse(content_type="text/javascript; charset=UTF-8", charset='UTF-8')
    serializers.serialize("json", queryset, stream=response)
    return response

export_as_json.short_description = "Exportar datos en formato json"

admin.site.add_action(export_as_json, 'export_as_json')


class UserProfileAdmin(SimpleHistoryAdmin):
    list_display = ['nombre_completo',]# 'get_barcode_url']
    list_filter = ['user__groups',]
    date_hierarchy = 'date_added'


class CustomerAdmin(admin.ModelAdmin):
    search_fields = ['name']
    date_hierarchy = 'date_added'
    list_display = ['name', 'phone_number', 'address', 'active']


class ProductAdmin(admin.ModelAdmin):
    search_fields = ['name']
    date_hierarchy = 'date_added'
    list_display = ['product', 'active', 'unitmeasurement']


class OriginDestinationRateAdmin(admin.ModelAdmin):
    search_fields = ['origin__name', 'destination__name']
    autocomplete_fields = ['origin', 'destination']
    date_hierarchy = 'date_added'
    list_display = ['origin', 'destination', 'rate']


admin.site.register(UserProfile, UserProfileAdmin)
admin.site.register(UnitMeasurement)
admin.site.register(Product, ProductAdmin)
admin.site.register(Customer, CustomerAdmin)
admin.site.register(OriginDestinationRate, OriginDestinationRateAdmin)
