from django.db import models
from django.contrib.auth import get_user_model
from products.models import ProductVariant

User = get_user_model()
# Create your models here.

class Cart(models.Model):
    cart_id = models.AutoField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    added_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Cart #{self.cart_id} - {self.user.email}"
