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
