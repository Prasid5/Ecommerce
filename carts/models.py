from django.db import models
from django.contrib.auth import get_user_model
from products.models import ProductVariant

User = get_user_model()

class Cart(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        if self.user:
            return f"Cart for {self.user.email}"

    @property
    def total_items(self):
        return self.items.count()

    @property
    def total_quantity(self):
        return sum(item.quantity for item in self.items.all())

    @property
    def total_cart_amount(self):
        return sum(item.item_amount for item in self.items.all())


class CartItem(models.Model):
    """
    Each cart can have multiple items.
    Each item refers to a specific product variant.
    """
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="items")
    variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE)

    quantity = models.PositiveIntegerField(default=1)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('cart', 'variant')  # ensures no duplicate variant rows

    def __str__(self):
        return f"{self.variant} x {self.quantity}"

    @property
    def price(self):
        return self.variant.product.base_price

    @property
    def item_amount(self):
        return self.price * self.quantity
