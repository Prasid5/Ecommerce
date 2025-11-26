from products.models import Brand, Category
def categories_and_brands(request):
    categories = Category.objects.all().order_by('category_name')
    brands = Brand.objects.all().order_by('brand_name')
    return {
        'home_categories': categories,
        'home_brands': brands,
    }