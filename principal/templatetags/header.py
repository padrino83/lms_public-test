from django import template
from django.conf import settings
from django.db.models import Q
from django.utils import timezone

from lmsapp.models import Customer, Order

register = template.Library()

@register.inclusion_tag("header.html", takes_context=True)
def get_header(context):
    now = timezone.now()
    request = context['request']
    q = request.GET.get('q', '')
    if request.user.userprofile and request.user.userprofile.is_operator():
        alarms = Order.objects.filter(Q(status='pending') | Q(price__lte=0)).filter(date_order__range=(now.replace(hour=0, minute=0, second=0), now.replace(hour=23, minute=59, second=59)))
    else:
        alarms = []
    
    return {
        "STATIC_URL": settings.STATIC_URL,
        'user': request.user,
        'path': request.path,
        'q': q,
        'alarms': alarms,
    }


@register.inclusion_tag("sidebar.html", takes_context=True)
def get_sidebar(context):
    request = context['request']
    q = request.GET.get('q', '')
    alarms = []
    
    return {
        "STATIC_URL": settings.STATIC_URL,
        'user': request.user,
        'path': request.path,
        'q': q,
        'alarms': alarms,
    }
