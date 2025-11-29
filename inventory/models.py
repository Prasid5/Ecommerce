from django.db import models
from products.models import ProductVariant

class Stock(models.Model):
    productvariant = models.OneToOneField(ProductVariant, on_delete=models.CASCADE, related_name='inventorystocks')
    quantity = models.IntegerField(default=0)
    cost_per_unit = models.FloatField(default=0)
    total_cost = models.FloatField(default=0)


class StockTransaction(models.Model):
    productvariant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE,related_name='stocktransactions')
    change = models.IntegerField()  # + for stock in, - for stock out
    transaction_cost = models.FloatField(default=0)
    reason = models.CharField(max_length=255)
    timestamp = models.DateTimeField(auto_now_add=True)

    @property
    def type(self):
        return "Stock In" if self.change > 0 else "Stock Out"

# Create your models here.
