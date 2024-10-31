#! -*- coding: utf-8 -*-
from django import template
from django.conf import settings
from django.template import Context
from django.template import RequestContext
from django.contrib.auth.forms import AuthenticationForm
from django.utils import timezone

from lmsapp.models import Customer

register = template.Library()

@register.inclusion_tag("rightbar.html", takes_context=True)
def get_rightbar(context):
    request = context['request']
    q = request.GET.get('q', '')
    customers = Customer.objects.all()[:10]
    
    return {
        "STATIC_URL": settings.STATIC_URL,
        'user': request.user,
        'path': request.path,
        'q': q,
        'customers': customers,
    }
