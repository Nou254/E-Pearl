from django.contrib import admin

# Register your models here.
from django.contrib import admin
from .models import Event, TicketTier, Ticket

@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ['event_name', 'venue', 'event_date', 'status', 'max_capacity']
    list_filter = ['status']

@admin.register(TicketTier)
class TicketTierAdmin(admin.ModelAdmin):
    list_display = ['tier_name', 'event', 'price', 'quantity_limit', 'quantity_sold']

@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ['ticket_code', 'customer_name', 'event', 'price', 'status']
    list_filter = ['status']