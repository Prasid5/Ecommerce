from django.db import models
from django.utils.text import slugify
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey

# -------------------------
# CATEGORY MODEL
# -------------------------
class Category(models.Model):
    category_name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)
    slug = models.SlugField(unique=True, blank=True, null=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.category_name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.category_name


# -------------------------
# PRODUCT MODEL
# -------------------------
class Product(models.Model):
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, related_name='products')
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    brand = models.CharField(max_length=100, blank=True)
    material = models.CharField(max_length=100, blank=True, help_text="e.g., Mesh, Leather, Synthetic")
    base_price = models.DecimalField(max_digits=10, decimal_places=2)
    main_image = models.ImageField(upload_to='images/products/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    slug = models.SlugField(unique=True, blank=True, null=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


# -------------------------
# PRODUCT VARIANT MODEL
# -------------------------
class ProductVariant(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='variants')
    variant_name = models.CharField(max_length=100, default="Standard Variant")
    color = models.CharField(max_length=50)
    size = models.CharField(max_length=10)
    stock = models.PositiveIntegerField(default=0)
    sku = models.CharField(max_length=100, unique=True, blank=True, null=True)

    # Images (4 angles)
    top_image = models.ImageField(upload_to='images/variants/', blank=True, null=True)
    right_image = models.ImageField(upload_to='images/variants/', blank=True, null=True)
    left_image = models.ImageField(upload_to='images/variants/', blank=True, null=True)
    back_image = models.ImageField(upload_to='images/variants/', blank=True, null=True)

    def __str__(self):
        return f"{self.product.name} - {self.variant_name} ({self.color}, {self.size})"
