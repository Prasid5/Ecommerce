from django.conf import settings
from django.conf.urls.static import static
from django.urls import path
from products import views
urlpatterns = [
    path('product/<slug:slug>/', views.productdetails, name='productdetails'),
    path('categories/', views.categories, name="categories"),
    # path('brand/', views.brand, name="brand"),
    path('brand/<slug:brand_slug>/',views.brand_view, name='brand'),
    path('addbrand/', views.addbrand, name="addbrand"),
    path('addcategory/', views.addcategory, name="addcategory"),
    path('addproduct/', views.addproduct, name="addproduct"),
    path('addproductvariant/', views.addproductvariant, name="addproductvariant"),
    path('productlist/', views.productlist, name="productlist"),

    path("variants/", views.variantlist, name="variantlist"),
    path("variants/<slug:product_slug>/", views.variantlist, name="variantlist_by_product"),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
