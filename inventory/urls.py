from django.conf import settings
from django.conf.urls.static import static
from django.urls import path
from inventory import views
urlpatterns = [
    path("addstock/", views.addstock, name="addstock"),
    path("stocktracking/", views.stocktracking, name="stocktracking"),
    path("managestock/", views.managestock, name="managestock"),
    path("stockin/", views.stocktransaction, name="stockin"),
    path("stocktransaction/", views.stocktransaction, name="stocktransaction"),
]