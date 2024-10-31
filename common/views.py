from django.shortcuts import render, HttpResponse, get_object_or_404
from django.http import HttpResponseRedirect, Http404
from django.http import FileResponse
from django.contrib import messages
from django.utils.decorators import method_decorator
from django.utils.html import escape
from django import forms
from django.core.mail import send_mail
from django.core.paginator import Paginator, InvalidPage, EmptyPage, PageNotAnInteger
from django.conf import settings
from django.contrib.auth.decorators import login_required, permission_required, user_passes_test
from django.utils import timezone

import json

from dal import autocomplete

from .models import UserProfile, Customer
from .forms import UserForm, UserEditForm, UserProfileForm
from .forms import ContactForm, CustomerForm

# Create your views here.

@login_required
def handlePopAdd(request, addForm, field):
    if request.method == "POST":
        form = addForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                newObject = form.save(commit=False)
                newObject.added_for = request.user
                newObject.save()
            except:
                newObject = None
            if newObject:
                return HttpResponse('<script type="text/javascript">opener.dismissAddAnotherPopup(window, "%s", "%s");</script>' % (escape(newObject._get_pk_val()), escape(newObject)))
    else:
        form = addForm()

    pageContext = {'form': form, 'field': field}
    return render(request, "add/popadd.html", pageContext)


class LoginRequiredMixin(object):
    @classmethod
    def as_view(cls, **initkwargs):
        view = super(LoginRequiredMixin, cls).as_view(**initkwargs)
        return login_required(view)


class LoggedInMixin(object):
    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super(LoggedInMixin, self).dispatch(*args, **kwargs)


def permissions_required(perm, login_url=None, raise_exception=False):
    """
    Decorator for views that checks whether a user has a particular permission
    enabled, redirecting to the log-in page if necessary.
    If the raise_exception parameter is given the PermissionDenied exception
    is raised.
    """
    def check_perms(user):
        if not isinstance(perm, (list, tuple)):
            perms = (perm, )
        else:
            perms = perm
        # First check if the user has the permission (even anon users)
        if user.has_perms(perms):
            return True
        for p in perms:
            if not p in user.get_all_permissions():
                return False
        # In case the 403 handler should be called raise the exception
        if raise_exception:
            raise PermissionDenied
        # As the last resort, show the login form
        return False
    return user_passes_test(check_perms, login_url=login_url)


def user_admin(user):
    return user.is_superuser

def user_allowed(user):
    return user.userprofile().count()

def user_tramitador(user):
    return user.groups.filter(name='tramitador').exists()

def user_operador(user):
    return user.groups.filter(name='operador').exists()


@login_required
def edit_profile(request):
    """Edit UserProfile."""
    user = request.user
    try:
        profile = user.userprofile
    except:
        raise Http404

    user_form = UserEditForm(instance=user)
    form = UserProfileForm(instance=profile)

    if request.method == 'POST' and user and profile:
        form = UserProfileForm(request.POST, request.FILES, instance=profile)
        user_form = UserEditForm(request.POST, instance=user)
        if user_form.is_valid() and form.is_valid():
            user_form.save()
            form.save()
            messages.add_message(request, messages.INFO, 'Profile updated.')

    if (request.user.is_authenticated and request.user==user and request.user.userprofile) or request.user.is_superuser :
        return render(request, "common/accounts_profile.html", {'user': user, 'profile': profile, 'form': form, 'user_form': user_form,})
    return HttpResponseRedirect('/')


def contact(request):
    u"""Contact page view."""
    if request.method == 'POST':
        form = ContactForm(request.POST)
        if request.user.is_authenticated:
            form.initial = {'from_email': request.user.email, 'name': request.user.username}
            form.fields['email'].widget = forms.HiddenInput()
            form.fields['name'].widget = forms.HiddenInput()
        if form.is_valid():
            try:
                send_mail(settings.EMAIL_SUBJECT_PREFIX, 'EMAIL: ' + form.cleaned_data['name'] + ' <' + form.cleaned_data['email'] + '>\n\nMessage: ' + form.cleaned_data['message'], settings.DEFAULT_FROM_EMAIL, [settings.DEFAULT_FROM_EMAIL])
                messages.add_message(request, messages.INFO, 'Gracias por escribirnos.')
            except:
                messages.add_message(request, messages.INFO, 'No se pudo enviar el mensaje.')              
            return HttpResponseRedirect('/')
    else:
        form = ContactForm()
        if request.user.is_authenticated:
            form.initial = {'from_email': request.user.email, 'name': request.user.username}
            form.fields['email'].widget = forms.HiddenInput()
            form.fields['name'].widget = forms.HiddenInput()
    
    data = {
        'form': form,
    }
    
    return render(request, 'common/contact.html', data)


@login_required
def show_barcode(request, pk):
    if request.user.is_staff:
        persona = get_object_or_404(UserProfile, pk=pk)
    else:
        persona = get_object_or_404(UserProfile, user=request.user)
    
    barcode = open(persona.get_barcode(), 'rb')
    
    return FileResponse(barcode)


def permission_denied(request):
    return render(request, 'error_permission_required.html', {})


def error_permission_required(request):
    return render(request, "error_permission_required.html", {})


def error_400(request):
    return render(request, "400.html", {})


def error_403(request):
    return render(request, "403.html", {})


def error_404(request):
    return render(request, "404.html", {})


def error_500(request):
    return render(request, "500.html", {})


#
# @login_required
# @user_passes_test(user_tramitador_empresa, login_url='/common/permission_denied/')
# def listado_empresas(request):
#     return render(request, 'common/listado_empresas.html', {})
#
#
# @login_required
# @user_passes_test(user_tramitador, login_url='/common/permission_denied/')
# def add_consultorio(request):
#     return handlePopAdd(request, ConsultorioForm, 'consultorio')


########################################################################
################                Customer            ####################
########################################################################


@login_required
@permission_required('lmsapp.add_customer', raise_exception=True)
def add_customer(request):

    if request.method == 'POST':
        form = CustomerForm(request.POST)
        if form.is_valid():
            customer = form.save()
            customer.added_for = request.user
            customer.save()
            return HttpResponseRedirect(reverse('customers_list'))
    else:
        form = CustomerForm()

    data = {
        'form':  form,
    }
    return render(request, "common/add_customer.html", data)


@login_required
@permission_required('lmsapp.change_customer', raise_exception=True)
def edit_customer(request, pk):
    customer = get_object_or_404(Customer, pk=pk)

    if request.method == 'POST':
        form = CustomerForm(request.POST, instance=customer)
        if form.is_valid():
            customer = form.save()
            customer.added_for = request.user
            customer.save()
            return HttpResponseRedirect(reverse('customers_list'))
    else:
        form = CustomerForm(instance=customer)

    data = {
        'customer': customer,
        'form': form,
    }
    return render(request, "common/add_customer.html", data)


@login_required
@permission_required('lmsapp.view_customer', raise_exception=True)
def customers_list(request):
    customers_list = Customer.objects.all()
    filters = {}

    q = request.GET.get('q', '')

    if q:
        filters['q'] = q
        customers_list = customers_list.filter(Q(name__icontains=q)).distinct()

    paginator = Paginator(customers_list, 10)  # Show 10 consultas per page

    page = request.GET.get('page')
    try:
        customers = paginator.page(page)
    except PageNotAnInteger:
        # If page is not an integer, deliver first page.
        customers = paginator.page(1)
    except EmptyPage:
        # If page is out of range (e.g. 9999), deliver last page of results.
        customers = paginator.page(paginator.num_pages)

    data = {
        'q': q,
        'customers': customers,
    }
    return render(request, "common/customers_list.html", data)


class CustomerAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        if not self.request.user.is_authenticated:
            return Customer.objects.none()

        qs = Customer.objects.all()

        if self.q:
            qs = qs.filter(name__icontains=self.q)

        return qs
