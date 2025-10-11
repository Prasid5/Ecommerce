from django.conf import settings
from django.conf.urls.static import static
from django.urls import path
from products import views
urlpatterns = [
    path('productdetails/', views.productdetails, name="productdetails"),
    path('categories/', views.categories, name="categories"),
    path('brands/', views.brands, name="brands"),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
