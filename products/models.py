from django.db import models

class Category(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name

class Product(models.Model):
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    brand = models.CharField(max_length=100, blank=True)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, related_name='products')

    gender = models.CharField(
        max_length=10,
        choices=[('Men', 'Men'), ('Women', 'Women'), ('Unisex', 'Unisex')],
        default='Unisex'
    )

    material = models.CharField(max_length=200, blank=True, help_text="e.g., Mesh upper with EVA sole")

    base_price = models.DecimalField(max_digits=10, decimal_places=2)
    main_image = models.ImageField(upload_to='images/products/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class ProductVariant(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='variants')
    size = models.CharField(max_length=10)
    color = models.CharField(max_length=50)
    stock_quantity = models.IntegerField(default=0)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    sku = models.CharField(max_length=100, unique=True)

    front_image = models.ImageField(upload_to='images/variants/', blank=True, null=True)
    top_image = models.ImageField(upload_to='images/variants/', blank=True, null=True)
    side_image = models.ImageField(upload_to='images/variants/', blank=True, null=True)
    back_image = models.ImageField(upload_to='images/variants/', blank=True, null=True)

    def __str__(self):
        return f'{self.product.name} - {self.color} - {self.size}'
