from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Payment

@receiver(post_save, sender=Payment)
def update_order_payment_status(sender, instance, **kwargs):

    order = instance.order

    if instance.payment_status == 'success':
        order.status = 'processing'
    elif instance.payment_status == 'failed':
        order.status = 'cancelled'
    else:
        order.status = 'pending'

    order.save()
