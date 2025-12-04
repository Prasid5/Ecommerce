from django.shortcuts import render
# Create your views here.
def shippingaddress(request):
    return render(request, 'shippingaddress.html')

def order(request):
    return render(request, 'order.html')
