import os
from django.db.models.signals import post_delete
from django.dispatch import receiver
from .models import Brand, Product, ProductVariant

# -------------------------
# DELETE IMAGE HELPER
# -------------------------
def delete_file(field):
    """
    Safely deletes file only if it exists in filesystem.
    Works for FileField, ImageField, and remote storage.
    """
    try:
        if field and hasattr(field, "path") and os.path.isfile(field.path):
            os.remove(field.path)
        else:
            # For S3, Cloudinary, Azure etc.
            if field and field.storage.exists(field.name):
                field.storage.delete(field.name)
    except Exception:
        pass  # avoids crashes

# -------------------------
# BRAND IMAGE DELETION
# -------------------------
@receiver(post_delete, sender=Brand)
def delete_brand_images(sender, instance, **kwargs):
    delete_file(instance.brand_logo)
    delete_file(instance.brand_picture)

# -------------------------
# PRODUCT IMAGE DELETION
# -------------------------
@receiver(post_delete, sender=Product)
def delete_product_image(sender, instance, **kwargs):
    delete_file(instance.main_image)

# -------------------------
# PRODUCT VARIANT IMAGE DELETION
# -------------------------
@receiver(post_delete, sender=ProductVariant)
def delete_variant_images(sender, instance, **kwargs):
    for img_field in ["top_image", "right_image", "left_image", "back_image"]:
        delete_file(getattr(instance, img_field))
