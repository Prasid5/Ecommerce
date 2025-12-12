from django.db import models
from users.models import User, ShippingAddress
from products.models import ProductVariant
from carts.models import Cart, CartItem

class Order(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('processing', 'Processing'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders')
    order_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    shipping_address = models.ForeignKey(ShippingAddress, on_delete=models.SET_NULL, null=True, related_name='orders')
    shipping_fee = models.DecimalField(max_digits=10, decimal_places=2, default=100)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    class Meta:
        ordering = ['-order_date']

    def __str__(self):
        return f'Order {self.id} by {self.user.email}'


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    total_orderitem_amount= models.DecimalField(max_digits=10, decimal_places=2, default='0')

    @property
    def subtotal(self):
        return self.quantity * self.price

    def __str__(self):
        return f'{self.variant.product.product_name} x {self.quantity} in Order {self.order.id}'