from products.models import Brand, Category, Product
from django.http import JsonResponse
from django.db.models import Q
def categories_and_brands(request):
    categories = Category.objects.all().order_by('category_name')
    brands = Brand.objects.all().order_by('brand_name')
    return {
        'home_categories': categories,
        'home_brands': brands,
    }

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
            'url': f'/product/{product.slug}/',  # Adjust to match your URL pattern
        })
    
    return JsonResponse({'products': results})