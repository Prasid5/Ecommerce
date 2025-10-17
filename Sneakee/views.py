from django.shortcuts import render
from django.views.decorators.cache import never_cache
from django.contrib.auth.decorators import login_required

@never_cache
def home(request):
    return render(request,"customer/home.html")

@never_cache
@login_required
def admindashboard(request):
    return render(request, "administrator/dashboard.html")

@never_cache
@login_required
def productdashboard(request):
    return render(request, "administrator/productdashboard.html")

@never_cache
@login_required
def userdashboard(request):
    return render(request, "administrator/userdashboard.html")

@never_cache
@login_required
def salesdashboard(request):
    return render(request, "administrator/salesdashboard.html")

@never_cache
@login_required
def orderdashboard(request):
    return render(request, "administrator/orderdashboard.html")