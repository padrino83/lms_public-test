from django.shortcuts import render
from django.contrib import messages

def driver_input(request):
    if request.method == 'POST':
        messages.success(request, "Form submitted successfully!")
    return render(request, 'driver_input.html')
