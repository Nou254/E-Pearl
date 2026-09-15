# orders/models.py

from django.db import models
from core.models import BaseModel
from django.utils import timezone


class MenuCategory(BaseModel):
    venue = models.ForeignKey(
        'venues.Venue',
        on_delete=models.CASCADE,
        related_name='menu_categories'
    )
    category_name = models.CharField(max_length=100)
    category_description = models.TextField(blank=True, null=True)
    display_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'menu_categories'
        ordering = ['display_order', 'category_name']
        unique_together = ['venue', 'category_name']

    def __str__(self):
        return self.category_name


class MenuItem(BaseModel):
    ITEM_TYPES = [
        ('food', 'Food'),
        ('beverage', 'Beverage'),
    ]

    venue = models.ForeignKey(
        'venues.Venue',
        on_delete=models.CASCADE,
        related_name='menu_items'
    )
    category = models.ForeignKey(
        MenuCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='items'
    )
    item_name = models.CharField(max_length=255)
    item_description = models.TextField(blank=True, null=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    image_url = models.CharField(max_length=255, blank=True, null=True)
    item_type = models.CharField(max_length=20, choices=ITEM_TYPES)
    is_active = models.BooleanField(default=True)
    is_available = models.BooleanField(default=True)
    display_order = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = 'menu_items'
        ordering = ['display_order', 'item_name']
        unique_together = ['venue', 'item_name']

    def __str__(self):
        return f"{self.item_name} ({self.get_item_type_display()})"


class Modifier(BaseModel):
    venue = models.ForeignKey(
        'venues.Venue',
        on_delete=models.CASCADE,
        related_name='modifiers'
    )
    menu_item = models.ForeignKey(
        MenuItem,
        on_delete=models.CASCADE,
        related_name='modifiers'
    )
    modifier_name = models.CharField(max_length=100)
    modifier_options = models.JSONField(default=list, help_text="List of options with prices")
    is_required = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'modifiers'

    def __str__(self):
        return f"{self.modifier_name} for {self.menu_item.item_name}"


class Order(BaseModel):
    ORDER_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('in_progress', 'In Progress'),
        ('ready', 'Ready'),
        ('served', 'Served'),
        ('cancelled', 'Cancelled'),
    ]

    venue = models.ForeignKey(
        'venues.Venue',
        on_delete=models.CASCADE,
        related_name='orders'
    )
    guest_session = models.ForeignKey(
        'guest_sessions.GuestSession',
        on_delete=models.CASCADE,
        related_name='orders'
    )
    order_status = models.CharField(max_length=20, choices=ORDER_STATUS_CHOICES, default='pending')
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    order_time = models.DateTimeField(default=timezone.now)
    ready_time = models.DateTimeField(null=True, blank=True)
    served_time = models.DateTimeField(null=True, blank=True)
    served_by = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='served_orders'
    )
    table = models.ForeignKey(
        'tables.Table',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='orders'
    )

    class Meta:
        db_table = 'orders'
        ordering = ['-order_time']

    def __str__(self):
        return f"Order {self.id} - {self.guest_session} ({self.order_status})"

    def calculate_total(self):
        total = self.items.aggregate(total=models.Sum('total_price'))['total'] or 0
        self.total_amount = total
        self.save()
        return total


class OrderItem(BaseModel):
    ITEM_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('preparing', 'Preparing'),
        ('ready', 'Ready'),
        ('served', 'Served'),
        ('cancelled', 'Cancelled'),
    ]

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    venue = models.ForeignKey('venues.Venue', on_delete=models.CASCADE, related_name='order_items')
    menu_item = models.ForeignKey(MenuItem, on_delete=models.SET_NULL, null=True, blank=True, related_name='order_items')
    item_name = models.CharField(max_length=255)
    item_type = models.CharField(max_length=20, choices=MenuItem.ITEM_TYPES)
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    modifiers = models.JSONField(default=list, blank=True)
    item_status = models.CharField(max_length=20, choices=ITEM_STATUS_CHOICES, default='pending')
    guest = models.ForeignKey(
        'guest_sessions.GuestSession',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='order_items',
        help_text="Specific guest who ordered this item (for group orders)"
    )

    priority = models.PositiveSmallIntegerField(default=0, help_text="Higher value = higher priority (0=normal)")

    # NEW: Mark items reassigned from host to self‑pay guest
    reassigned_from_host = models.BooleanField(
        default=False,
        help_text="True if this item was reassigned from the host to a guest for self‑payment"
    )

    class Meta:
        db_table = 'order_items'

    def __str__(self):
        return f"{self.quantity}x {self.item_name} ({self.item_status})"

    def save(self, *args, **kwargs):
        if not self.total_price or self.total_price == 0:
            self.total_price = self.unit_price * self.quantity
        super().save(*args, **kwargs)

    def mark_reassigned(self):
        self.reassigned_from_host = True
        self.save(update_fields=['reassigned_from_host'])