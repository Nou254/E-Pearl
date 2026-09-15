from django.contrib import admin

# Register your models here.
from django.contrib import admin
from .models import Order, OrderItem

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['id', 'guest_session', 'order_status', 'total_amount', 'order_time']
    list_filter = ['order_status']
    search_fields = ['guest_session__guest_name']

@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ['order', 'item_name', 'quantity', 'total_price', 'item_status']
    list_filter = ['item_status', 'item_type']