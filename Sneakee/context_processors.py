from products.models import Brand, Category, Product
from django.http import JsonResponse
from django.db.models import Q
def categories_and_brands(request):
    """
    Returns unique category names (grouped) and all brands
    """
    # Get all categories and extract unique category names
    all_categories = Category.objects.all().order_by('category_name')
    
    # Group categories by name - only show unique category names
    seen_names = set()
    unique_categories = []
    for category in all_categories:
        if category.category_name not in seen_names:
            unique_categories.append(category)
            seen_names.add(category.category_name)
    
    brands = Brand.objects.all().order_by('brand_name')
    
    return {
        'home_categories': unique_categories,
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