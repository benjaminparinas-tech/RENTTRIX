from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.db.models.signals import post_save
from django.dispatch import receiver

class Room(models.Model):
    room_number = models.CharField(max_length=10, unique=True)
    capacity = models.IntegerField(default=4)
    current_occupants = models.IntegerField(default=0)
    status = models.CharField(max_length=10, choices=[('vacant', 'Vacant'), ('full', 'Full')], default='vacant')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Room {self.room_number}"

    def update_status(self):
        if self.current_occupants >= self.capacity:
            self.status = 'full'
        else:
            self.status = 'vacant'
        self.save()

class RoomTenant(models.Model):
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name='tenants')
    tenant = models.ForeignKey(User, on_delete=models.CASCADE, related_name='room_assignments')
    move_in_date = models.DateField(default=timezone.now)
    status = models.CharField(max_length=10, choices=[('active', 'Active'), ('inactive', 'Inactive')], default='active')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['room', 'tenant']

    def __str__(self):
        return f"{self.tenant.get_full_name()} - Room {self.room.room_number}"

class Payment(models.Model):
    tenant = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payments')
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_month = models.DateField()
    payment_date = models.DateField(default=timezone.now)
    status = models.CharField(max_length=10, choices=[('paid', 'Paid'), ('unpaid', 'Unpaid')], default='unpaid')
    receipt_number = models.CharField(max_length=20, unique=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    year = models.IntegerField(default=2025)  # Default year is 2025

    def __str__(self):
        return f"Payment {self.receipt_number} - {self.tenant.get_full_name()}"

    def save(self, *args, **kwargs):
        if not self.receipt_number:
            timestamp = timezone.now().strftime('%Y%m%d%H%M%S')
            self.receipt_number = f"RCPT-{timestamp}-{self.tenant.id}"
        self.year = self.payment_month.year
        super().save(*args, **kwargs)

class Receipt(models.Model):
    payment = models.OneToOneField(Payment, on_delete=models.CASCADE, related_name='receipt')
    receipt_number = models.CharField(max_length=20, unique=True)
    tenant_name = models.CharField(max_length=100)
    room_number = models.CharField(max_length=10)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_month = models.DateField()
    payment_date = models.DateField()
    landlord_signature = models.ImageField(upload_to='signatures/', null=True, blank=True)
    generated_date = models.DateTimeField(auto_now_add=True)
    pdf_path = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return f"Receipt {self.receipt_number}"

class LandlordProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='landlord_profile')
    signature = models.ImageField(upload_to='signatures/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Landlord Profile - {self.user.get_full_name()}"

class AddOn(models.Model):
    room_tenant = models.ForeignKey(RoomTenant, on_delete=models.CASCADE, related_name='addons')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.CharField(max_length=200)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.description} - {self.amount} for {self.room_tenant.tenant.get_full_name()}"
    
    class Meta:
        ordering = ['-created_at']


class TenantSecurityProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='security_profile')
    force_password_change = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Security profile for {self.user.username}"


@receiver(post_save, sender=User)
def create_security_profile(sender, instance, created, **kwargs):
    """
    Ensure every non-staff user gets a security profile so we can
    enforce first-login password changes.
    """
    if created and not instance.is_staff:
        TenantSecurityProfile.objects.create(user=instance)
