"""
URL configuration for Sneakee project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from Sneakee import views
urlpatterns = [
    path('admin/', admin.site.urls),
    path('home/',views.home, name="home"),
    path('admindashboard/',views.admindashboard, name="admindashboard"),
    path('productdashboard/',views.productdashboard, name="productdashboard"),
    path('userdashboard/',views.userdashboard, name="userdashboard"),
    path('salesdashboard/',views.salesdashboard, name="salesdashboard"),

    path('',include('users.urls')),#No prefix
    path('',include('carts.urls')),
    path('',include('products.urls')),
    path('',include('orders.urls'))
]
