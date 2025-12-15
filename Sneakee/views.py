from django.shortcuts import render
from django.views.decorators.cache import never_cache
from django.contrib.auth.decorators import login_required, user_passes_test

from products.models import Brand, Category, Product, ProductVariant
from orders.models import Order
from users.models import User
from inventory.models import Stock

from django.db.models import Count, F, Q, Sum
from django.http import JsonResponse


def is_admin(user):
    return user.is_staff or user.is_superuser

def search_products(request):
    query = request.GET.get('q', '').strip()
    
    if len(query) < 2:  # Minimum 2 characters to search
        return JsonResponse({'products': []})
    
    # Search in product name and description, only active products
    products = Product.objects.filter(
        Q(product_name__icontains=query) | Q(description__icontains=query),
        is_active=True
    )[:8]  # Limit to 8 results
    
    results = []
    for product in products:
        results.append({
            'name': product.product_name,
            'slug': product.slug,
            'url': f'/product/{product.slug}/',  # Adjust URL pattern as needed
        })
    
    return JsonResponse({'products': results})

def home(request):
    products = Product.objects.all().order_by('-id')
    brands = Brand.objects.all().order_by('brand_name')
    
    casual_product = Product.objects.filter(
        category__category_name__iexact='Casual',
        is_active=True
    ).first()
    
    sport_product = Product.objects.filter(
        category__category_name__iexact='Sport Shoes',
        is_active=True
    ).first()
    
    context = {
        'brands': brands,
        'products': products,
        'casual_product': casual_product,
        'sport_product': sport_product,
    }
    return render(request, 'customer/home.html', context)


@never_cache
@login_required
@user_passes_test(is_admin)
def admindashboard(request):
    orders = Order.objects.filter(
        status__in=["pending", "confirmed"]
    ).order_by("-order_date")[:10]
    total_orders=Order.objects.count()
    total_products=Product.objects.count()
    total_stocks = Stock.objects.aggregate(total=Sum('quantity'))['total'] or 0

    total_revenue = Order.objects.filter(status='delivered').aggregate(
        total=Sum('total_amount')
    )['total'] or 0

    context={
        'orders':orders,
        'total_revenue':total_revenue,
        'total_products':total_products,
        'total_orders': total_orders,
        'total_stocks':total_stocks,
    }
    return render(request, "administrator/dashboard.html", context)


@never_cache
@login_required
@user_passes_test(is_admin)
def productdashboard(request):
    return render(request, "administrator/productdashboard.html")


@never_cache
@login_required
@user_passes_test(is_admin)
def userdashboard(request):
    total_admin=User.objects.filter(is_staff=True).count()
    total_customer=User.objects.filter(is_staff=False).count()
    total_active_customer = User.objects.filter(
        Q(is_staff=False) & Q(is_active=True)
    ).count()

    total_deactivated_customer = User.objects.filter(
        Q(is_staff=False) & Q(is_active=False)
    ).count()

    context={
        "total_admin":total_admin,
        "total_customer":total_customer,
        "total_active_customer":total_active_customer,
        "total_deactivated_customer":total_deactivated_customer,
    }
    return render(request, "administrator/userdashboard.html", context)


@never_cache
@login_required
@user_passes_test(is_admin)
def orderdashboard(request):
    total_orders = Order.objects.count()
    
    # Active = pending + confirmed + processing + shipped
    active_orders = Order.objects.filter(
        status__in=['pending', 'confirmed', 'processing', 'shipped']
    ).count()
    
    completed_orders = Order.objects.filter(status='delivered').count()
    cancelled_orders = Order.objects.filter(status='cancelled').count()
    
    context = {
        'total_orders': total_orders,
        'active_orders': active_orders,
        'completed_orders': completed_orders,
        'cancelled_orders': cancelled_orders,
    }
    
    return render(request, "administrator/orderdashboard.html", context)

@never_cache
@login_required
@user_passes_test(is_admin)
def inventorydashboard(request):
    if request.user.is_staff:
        low_stock_variants = ProductVariant.objects.filter(
            Q(inventorystocks__quantity__lte=F('low_stock_threshold')) |
            Q(inventorystocks__isnull=True)
        ).distinct()
        return render(request, "administrator/inventorydashboard.html", {
            "low_stock_variants": low_stock_variants
        })