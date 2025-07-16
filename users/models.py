from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager

class UserManager(BaseUserManager):
    def create_user(self, email, name, password=None, role='customer', **extra_fields):
        if not email:
            raise ValueError("User must have an email address")
        email=self.normalize_email(email)
        user=self.model(email=email, name=name, role=role, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_superuser(self, email, name, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(email, name, password, role='admin', **extra_fields)
    
class User(AbstractBaseUser, PermissionsMixin):
    ROLE_CHOICES=(
        ('admin','Admin'),
        ('customer', 'Customer'),
    )
    name=models.CharField(max_length=100)
    email=models.EmailField(unique=True)
    role=models.CharField(max_length=10, choices=ROLE_CHOICES)
    phone=models.CharField(max_length=10,blank=True)
    address=models.CharField(max_length=100, blank=True)

    is_active=models.BooleanField(default=True)
    is_staff=models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    
    objects=UserManager()

    USERNAME_FIELD='email'
    REQUIRED_FIELDS=['name']

    def __str__(self):
        return self.email