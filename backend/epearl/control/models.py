# control/models.py

from django.db import models
from core.models import BaseModel
from django.contrib.postgres.search import SearchVectorField
from django.contrib.postgres.indexes import GinIndex


class PlatformAuditLog(BaseModel):
    ACTION_TYPES = [
        ('venue_approve', 'Venue Approval'),
        ('venue_reject', 'Venue Rejection'),
        ('venue_suspend', 'Venue Suspension'),
        ('venue_reactivate', 'Venue Reactivation'),
        ('subscription_change', 'Subscription Change'),
        ('permission_grant', 'Permission Grant'),
        ('permission_revoke', 'Permission Revoke'),
        ('role_create', 'Role Create'),
        ('role_update', 'Role Update'),
        ('role_delete', 'Role Delete'),
        ('user_deactivate', 'User Deactivation'),
        ('user_reactivate', 'User Reactivation'),
        ('sms_credit_adjust', 'SMS Credit Adjustment'),
        ('platform_setting_change', 'Platform Setting Change'),
        ('admin_login', 'Admin Login'),
        ('export_data', 'Data Export'),
    ]

    actor = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        related_name='audit_logs'
    )
    action_type = models.CharField(max_length=50, choices=ACTION_TYPES)
    target_model = models.CharField(max_length=100, blank=True, null=True)
    target_id = models.CharField(max_length=100, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    metadata = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        db_table = 'platform_audit_logs'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.action_type} by {self.actor} at {self.created_at}"


class VenueHealthMetrics(BaseModel):
    venue = models.ForeignKey(
        'venues.Venue',
        on_delete=models.CASCADE,
        related_name='health_metrics'
    )
    active_guests = models.PositiveIntegerField(default=0)
    occupied_tables = models.PositiveIntegerField(default=0)
    total_tables = models.PositiveIntegerField(default=0)
    pending_orders = models.PositiveIntegerField(default=0)
    revenue_today = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    transactions_today = models.PositiveIntegerField(default=0)
    staff_on_duty = models.PositiveIntegerField(default=0)
    open_tickets = models.PositiveIntegerField(default=0)
    avg_turnaround_minutes = models.PositiveIntegerField(default=0)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'venue_health_metrics'
        unique_together = ['venue']

    def __str__(self):
        return f"Metrics for {self.venue.business_name}"

    def occupancy_rate(self):
        if self.total_tables == 0:
            return 0
        return round((self.occupied_tables / self.total_tables) * 100, 1)


class HQNotification(BaseModel):
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ]
    CATEGORY_CHOICES = [
        ('venue_registration', 'New Venue Registration'),
        ('document_verification', 'Document Verification'),
        ('subscription_expiry', 'Subscription Expiry'),
        ('payment_failure', 'Payment Failure'),
        ('system_alert', 'System Alert'),
        ('support_ticket', 'Support Ticket'),
    ]

    title = models.CharField(max_length=255)
    message = models.TextField()
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES)
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='medium')
    venue = models.ForeignKey(
        'venues.Venue',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='hq_notifications'
    )
    is_read = models.BooleanField(default=False)
    
    read_at = models.DateTimeField(null=True, blank=True)
    resolved_by = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='resolved_notifications'
    )
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolution_time_seconds = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = 'hq_notifications'
        ordering = ['-created_at']

    def __str__(self):
        return f"[{self.priority}] {self.title}"


class SupportTicket(BaseModel):
    STATUS_CHOICES = [
        ('open', 'Open'),
        ('in_progress', 'In Progress'),
        ('waiting', 'Waiting for Response'),
        ('resolved', 'Resolved'),
        ('closed', 'Closed'),
    ]
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]

    venue = models.ForeignKey(
        'venues.Venue',
        on_delete=models.CASCADE,
        related_name='support_tickets'
    )
    raised_by = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        related_name='raised_tickets'
    )
    assigned_to = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_tickets'
    )
    subject = models.CharField(max_length=255)
    description = models.TextField()
    category = models.CharField(max_length=50, default='general')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='medium')
    
    assigned_at = models.DateTimeField(null=True, blank=True)
    first_response_at = models.DateTimeField(null=True, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    response_time_seconds = models.PositiveIntegerField(default=0)
    resolution_time_seconds = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = 'support_tickets'
        ordering = ['-created_at']

    def __str__(self):
        return f"Ticket: {self.subject} ({self.status})"


class VenueAuditLog(BaseModel):
    ACTION_TYPES = [
        ('force_capture', 'Force Capture'),
        ('void_hold', 'Void Hold'),
        ('manual_override_exit', 'Manual Override Exit'),
        ('suspend_table', 'Suspend Table'),
        ('cash_collection', 'Cash Collection'),
        ('staff_scan_in', 'Staff Scan-In'),
        ('staff_scan_out', 'Staff Scan-Out'),
        ('shift_handover', 'Shift Handover'),
        ('manager_override', 'Manager Override'),
        ('table_status_change', 'Table Status Change'),
        ('order_cancellation', 'Order Cancellation'),
        ('payment_failure', 'Payment Failure'),
    ]

    venue = models.ForeignKey('venues.Venue', on_delete=models.CASCADE, related_name='venue_audit_logs')
    staff = models.ForeignKey('staff.Staff', on_delete=models.SET_NULL, null=True, blank=True, related_name='venue_audit_logs')
    guest_session = models.ForeignKey('guest_sessions.GuestSession', on_delete=models.SET_NULL, null=True, blank=True)
    table = models.ForeignKey('tables.Table', on_delete=models.SET_NULL, null=True, blank=True)

    action_type = models.CharField(max_length=50, choices=ACTION_TYPES)
    action_description = models.TextField()
    amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    reason = models.TextField(blank=True, null=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'venue_audit_logs'
        ordering = ['-timestamp']

    def save(self, *args, **kwargs):
        if self.pk:
            raise ValueError("Audit log entries are immutable and cannot be updated.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValueError("Audit log entries cannot be deleted.")


# =============================================================================
# Menu Builder Models
# =============================================================================

class MenuCategory(BaseModel):
    venue = models.ForeignKey(
        'venues.Venue',
        on_delete=models.CASCADE,
        related_name='control_menu_categories'
    )
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    display_order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'control_menu_categories'
        ordering = ['display_order', 'name']
        unique_together = ['venue', 'name']

    def __str__(self):
        return f"{self.venue.business_name} - {self.name}"


class MenuItem(BaseModel):
    ITEM_TYPES = [
        ('food', 'Food'),
        ('beverage', 'Beverage'),
    ]

    venue = models.ForeignKey(
        'venues.Venue',
        on_delete=models.CASCADE,
        related_name='control_menu_items'
    )
    category = models.ForeignKey(
        MenuCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='control_items'
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    image_url = models.CharField(max_length=500, blank=True, null=True)
    item_type = models.CharField(max_length=20, choices=ITEM_TYPES, default='food')
    is_active = models.BooleanField(default=True)
    is_available = models.BooleanField(default=True)
    display_order = models.IntegerField(default=0)

    stock_count = models.IntegerField(default=0)
    low_stock_threshold = models.IntegerField(default=5)

    # Full‑text search vector (optional)
    search_vector = SearchVectorField(null=True, blank=True)

    class Meta:
        db_table = 'control_menu_items'
        ordering = ['display_order', 'name']
        unique_together = ['venue', 'name']
        indexes = [
            GinIndex(fields=['search_vector']),
        ]

    def __str__(self):
        return f"{self.venue.business_name} - {self.name}"

    @property
    def is_low_stock(self):
        return self.stock_count <= self.low_stock_threshold

    @property
    def is_out_of_stock(self):
        return self.stock_count <= 0


class Modifier(BaseModel):
    venue = models.ForeignKey(
        'venues.Venue',
        on_delete=models.CASCADE,
        related_name='control_modifiers'
    )
    menu_item = models.ForeignKey(
        MenuItem,
        on_delete=models.CASCADE,
        related_name='control_modifiers'
    )
    name = models.CharField(max_length=100)
    options = models.JSONField(default=list, blank=True)
    is_required = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'control_modifiers'
        ordering = ['name']
        unique_together = ['venue', 'menu_item', 'name']

    def __str__(self):
        return f"{self.menu_item.name} - {self.name}"


# =============================================================================
# Onboarding & Stock Alert Models
# =============================================================================

class OnboardingProgress(BaseModel):
    venue = models.OneToOneField(
        'venues.Venue',
        on_delete=models.CASCADE,
        related_name='onboarding_progress'
    )
    step = models.PositiveSmallIntegerField(default=0)
    completed_at = models.DateTimeField(null=True, blank=True)
    documents_uploaded = models.BooleanField(default=False)
    owner_verified = models.BooleanField(default=False)
    profile_configured = models.BooleanField(default=False)
    floor_plan_configured = models.BooleanField(default=False)
    menu_configured = models.BooleanField(default=False)
    payment_configured = models.BooleanField(default=False)
    last_error = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'control_onboarding_progress'

    def __str__(self):
        return f"Onboarding {self.venue.business_name}: step {self.step}"


class StockAlertLog(BaseModel):
    venue = models.ForeignKey('venues.Venue', on_delete=models.CASCADE, related_name='stock_alerts')
    menu_item = models.ForeignKey(MenuItem, on_delete=models.CASCADE, related_name='stock_alerts')
    alert_sent_at = models.DateTimeField(auto_now_add=True)
    stock_count_at_alert = models.IntegerField()
    threshold_at_alert = models.IntegerField()
    resolved = models.BooleanField(default=False)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'control_stock_alert_logs'
        ordering = ['-alert_sent_at']

    def __str__(self):
        return f"Low stock alert: {self.menu_item.name} @ {self.alert_sent_at}"


# =============================================================================
# Wastage & Menu Versioning
# =============================================================================

class WastageLog(BaseModel):
    STATUS_CHOICES = [
        ('pending', 'Pending Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]

    venue = models.ForeignKey('venues.Venue', on_delete=models.CASCADE, related_name='wastage_logs')
    order_item = models.ForeignKey('orders.OrderItem', on_delete=models.SET_NULL, null=True, blank=True, related_name='wastage_logs')
    menu_item = models.ForeignKey(MenuItem, on_delete=models.SET_NULL, null=True, blank=True, related_name='wastage_logs')

    reason = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField(default=1)

    created_by = models.ForeignKey('users.User', on_delete=models.SET_NULL, null=True, related_name='created_wastage_logs')
    created_at = models.DateTimeField(auto_now_add=True)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    written_off_by = models.ForeignKey('users.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='written_off_wastage')
    written_off_at = models.DateTimeField(null=True, blank=True)
    resolution_notes = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'control_wastage_logs'
        ordering = ['-created_at']

    def __str__(self):
        return f"Wastage: {self.menu_item.name if self.menu_item else 'N/A'} - {self.amount}"


class MenuVersion(BaseModel):
    menu_item = models.ForeignKey(MenuItem, on_delete=models.CASCADE, related_name='versions')
    venue = models.ForeignKey('venues.Venue', on_delete=models.CASCADE, related_name='menu_versions')

    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    is_active = models.BooleanField(default=True)
    is_available = models.BooleanField(default=True)
    stock_count = models.IntegerField(default=0)
    low_stock_threshold = models.IntegerField(default=5)

    changed_by = models.ForeignKey('users.User', on_delete=models.SET_NULL, null=True, related_name='menu_changes')
    change_reason = models.CharField(max_length=255, blank=True, null=True)
    version_number = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'control_menu_versions'
        ordering = ['-created_at']
        unique_together = ['menu_item', 'version_number']

    def __str__(self):
        return f"{self.menu_item.name} v{self.version_number}"