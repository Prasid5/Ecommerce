from django.shortcuts import render

def productdetails(request):
    return render(request, 'productdetails.html')

def categories(request):
    return render(request,'categories.html')

def brands(request):
    return render(request, 'brands.html')
# Create your views here.
