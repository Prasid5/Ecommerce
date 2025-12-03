from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager

class UserManager(BaseUserManager):
    def create_user(self, email, username, password=None, **extra_fields):
        if not email:
            raise ValueError("User must have an email address")
        email=self.normalize_email(email)
        user=self.model(email=email, username=username, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_superuser(self, email, username, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(email, username, password, **extra_fields)
    
class User(AbstractBaseUser, PermissionsMixin):
    username=models.CharField(max_length=100)
    email=models.EmailField(unique=True)
    phone=models.CharField(max_length=10,blank=True)
    address=models.CharField(max_length=100, blank=True)
    is_active=models.BooleanField(default=True)
    is_staff=models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    
    objects=UserManager()

    USERNAME_FIELD='email'
    REQUIRED_FIELDS=['username']

    def __str__(self):
        return self.email
    
class ShippingAddress(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    location_of = models.CharField(max_length=50)
    province = models.CharField(max_length=100)
    district = models.CharField(max_length=100)
    city = models.CharField(max_length=100)
    address = models.CharField(max_length=255)
    landmark = models.CharField(max_length=255)
    streetorhouse_no = models.CharField(max_length=255)
    contact = models.CharField(max_length=20)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.location_of} - {self.city}"
