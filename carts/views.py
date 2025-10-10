from django.shortcuts import render

def cart(request):
    if request.method=='POST':
        pass
    return render(request,"cart.html")
# Create your views here.
