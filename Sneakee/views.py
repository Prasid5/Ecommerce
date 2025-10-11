from django.shortcuts import render
from django.views.decorators.cache import never_cache
from django.contrib.auth.decorators import login_required

@never_cache
def home(request):
    return render(request,"customer/home.html")

@never_cache
@login_required
def admindashboard(request):
    return render(request, "admin/dashboard.html")