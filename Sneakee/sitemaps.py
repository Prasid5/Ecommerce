from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from products.models import Product, Category

class ProductSitemap(Sitemap):
    changefreq = "daily"
    priority = 0.8

    def items(self):
        return Product.objects.filter(is_active=True)

    def lastmod(self, obj):
        # If you have updated_at field
        return obj.updated_at if hasattr(obj, 'updated_at') else None

    def location(self, obj):
        # Adjust this to match your actual URL pattern
        return f'/products/{obj.slug}/'


class CategorySitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.6

    def items(self):
        return Category.objects.all()

    def location(self, obj):
        # Adjust based on your URL structure
        if hasattr(obj, 'slug'):
            return f'/category/{obj.slug}/'
        else:
            return f'/category/{obj.id}/'


class StaticViewSitemap(Sitemap):
    priority = 0.5
    changefreq = 'monthly'

    def items(self):
        # Add your static page URL names here
        return ['home']  # Add others like 'about', 'contact' if you have them

    def location(self, item):
        return reverse(item)