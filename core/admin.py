from django.contrib import admin
from .models import Room, RoomTenant, Payment, Receipt

@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ('room_number', 'capacity', 'current_occupants', 'status', 'created_at')
    list_filter = ('status',)
    search_fields = ('room_number',)

@admin.register(RoomTenant)
class RoomTenantAdmin(admin.ModelAdmin):
    list_display = ('tenant', 'room', 'move_in_date', 'status', 'created_at')
    list_filter = ('status', 'room')
    search_fields = ('tenant__username', 'tenant__email', 'room__room_number')

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('receipt_number', 'tenant', 'room', 'amount', 'payment_month', 'payment_date', 'status')
    list_filter = ('status', 'payment_month')
    search_fields = ('receipt_number', 'tenant__username', 'tenant__email')

@admin.register(Receipt)
class ReceiptAdmin(admin.ModelAdmin):
    list_display = ('receipt_number', 'tenant_name', 'room_number', 'amount', 'payment_date', 'generated_date')
    search_fields = ('receipt_number', 'tenant_name', 'room_number')
