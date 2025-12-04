from django.db import models
from users.models import User, ShippingAddress
from products.models import ProductVariant
from carts.models import Cart, CartItem

class Order(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
    )
    PAYMENT_STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('failed', 'Failed'),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders')
    order_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    payment_status = models.CharField(max_length=10, choices=PAYMENT_STATUS_CHOICES, default='pending')
    shipping_address = models.ForeignKey(ShippingAddress, on_delete=models.SET_NULL, null=True, related_name='orders')
    cart = models.OneToOneField(Cart, on_delete=models.SET_NULL, null=True, blank=True)  # optional link
    shipping_fee = models.DecimalField(max_digits=10, decimal_places=2, default=100)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    def __str__(self):
        return f'Order {self.id} by {self.user.email}'

    def calculate_total(self):
        """
        Total = sum of OrderItem subtotal + shipping_fee per quantity
        """
        item_total = sum(item.subtotal for item in self.order_items.all())
        total_quantity = sum(item.quantity for item in self.order_items.all())
        self.total_amount = item_total + (self.shipping_fee * total_quantity)
        self.save()
        return self.total_amount


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='order_items')
    variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)  # Price at purchase time

    @property
    def subtotal(self):
        return self.quantity * self.price

    def __str__(self):
        return f'{self.variant} x {self.quantity} in Order {self.order.id}'
