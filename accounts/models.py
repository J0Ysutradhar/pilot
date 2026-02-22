from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models


class CustomUserManager(BaseUserManager):
    """Custom user manager where email is the unique identifier"""
    
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
        
        return self.create_user(email, password, **extra_fields)


class CustomUser(AbstractUser):
    """Custom user model with email as username"""
    username = None
    email = models.EmailField(unique=True)
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []
    
    objects = CustomUserManager()
    
    def __str__(self):
        return self.email
    
    def get_email_prefix(self):
        """Get the part of email before @ symbol"""
        return self.email.split('@')[0] if '@' in self.email else self.email


class UserProfile(models.Model):
    """User profile with additional information"""
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='profile')
    name = models.CharField(max_length=255, blank=True)
    profile_picture = models.ImageField(upload_to='profile_pictures/', blank=True, null=True)
    mobile_number = models.CharField(max_length=20, blank=True)
    home_address = models.TextField(blank=True)
    business_info = models.TextField(blank=True, help_text='Details about your business/Facebook page')
    
    # KYC Fields
    KYC_STATUS_CHOICES = (
        ('NONE', 'Not Submitted'),
        ('PENDING', 'Under Review'),
        ('VERIFIED', 'Verified'),
        ('REJECTED', 'Rejected'),
    )
    kyc_front_image = models.ImageField(upload_to='kyc_documents/front/', blank=True, null=True)
    kyc_back_image = models.ImageField(upload_to='kyc_documents/back/', blank=True, null=True)
    kyc_status = models.CharField(max_length=20, choices=KYC_STATUS_CHOICES, default='NONE')
    kyc_rejection_reason = models.TextField(blank=True, help_text='Reason for KYC rejection (shown to user)')
    
    # Subscription fields
    subscription_expiry = models.DateTimeField(null=True, blank=True)
    package_name = models.CharField(max_length=50, blank=True, default='Free Trial')
    
    def __str__(self):
        return f"{self.user.email}'s profile"

    def is_profile_complete(self):
        """Check if essential profile fields are filled"""
        required_fields = [self.name, self.mobile_number, self.home_address, self.business_info, self.profile_picture]
        return all(field for field in required_fields)
    
    def is_subscription_active(self):
        """Check if subscription is active"""
        from django.utils import timezone
        if not self.subscription_expiry:
            return True # Allow access if no expiry set (or change logic as needed)
        return timezone.now() < self.subscription_expiry


class AIAgentConfig(models.Model):
    """AI Agent configuration for each user"""
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='ai_config')
    is_active = models.BooleanField(default=True, help_text='Turn AI agent on/off')
    facebook_page_id = models.CharField(max_length=2000, blank=True)
    facebook_page_api= models.CharField(max_length=2000, blank=True)

    system_prompt = models.TextField(blank=True)
    google_sheet_id = models.CharField(max_length=200, blank=True, help_text='Google Sheet ID for reports')
    blocked_post_ids = models.TextField(blank=True, help_text='Newline-separated list of Facebook post IDs to block')
    
    def __str__(self):
        return f"{self.user.email}'s AI config"
    
    def get_webhook_url(self):
        """Generate webhook URL based on user's email"""
        email_prefix = self.user.get_email_prefix()
        return f"https://ftn8nbd.onrender.com/webhook/{email_prefix}"
    
    def get_blocked_post_ids_list(self):
        """Return blocked post IDs as a list"""
        if not self.blocked_post_ids:
            return []
        return [pid.strip() for pid in self.blocked_post_ids.strip().split('\n') if pid.strip()]


class SubscriptionHistory(models.Model):
    """Track history of user subscription packages"""
    profile = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='subscription_history')
    package_name = models.CharField(max_length=50)
    start_date = models.DateTimeField(auto_now_add=True)
    expiry_date = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.profile.user.email} - {self.package_name}"
    
    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = "Subscription Histories"


class PaymentRequest(models.Model):
    """Tracks manual payment requests submitted by user for subscription upgrades"""
    
    PAYMENT_METHOD_CHOICES = (
        ('BKASH', 'Bkash'),
        ('NAGAD', 'Nagad'),
        ('CRYPTO', 'Crypto (USDT/USDC)'),
    )
    
    STATUS_CHOICES = (
        ('PENDING', 'Pending'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
    )

    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='payment_requests')
    package_name = models.CharField(max_length=100)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES)
    transaction_id = models.CharField(max_length=255)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.email} - {self.package_name} ({self.status})"

    class Meta:
        ordering = ['-created_at']

