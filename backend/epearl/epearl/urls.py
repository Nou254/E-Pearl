from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

# =============================================================================
# Import Viewsets
# =============================================================================
from venues.views import VenueViewSet
from staff.views import (
    StaffViewSet,
    ShiftViewSet,
    ShiftStaffViewSet,
    StaffAttendanceViewSet,
    StaffReportViewSet,
)
from tables.views import ZoneViewSet, TableViewSet
from guest_sessions.views import GuestSessionViewSet
from orders.views import OrderViewSet, OrderItemViewSet
from payments.views import PreAuthHoldViewSet, TransactionViewSet, PaymentGatewayConfigViewSet
from events.views import EventViewSet, TicketTierViewSet, TicketViewSet
from explore.views import (
    BookingViewSet, RoomTypeViewSet,
    RoomAvailabilityViewSet, VenueHiringViewSet,
    PublicExploreViewSet
)
from gate.views import GateViewSet
from notifications.views import NotificationViewSet

# =============================================================================
# Import Authentication Views from Users App
# =============================================================================
from users.views import AuthViewSet, UserViewSet

# =============================================================================
# Router Configuration
# =============================================================================
router = DefaultRouter()

# Core apps
router.register(r'venues', VenueViewSet)
router.register(r'staff', StaffViewSet, basename='staff')
router.register(r'shifts', ShiftViewSet, basename='shifts')
router.register(r'shift-staff', ShiftStaffViewSet, basename='shift-staff')
router.register(r'reports', StaffReportViewSet, basename='staff-reports')
router.register(r'tables', TableViewSet, basename='tables')
router.register(r'zones', ZoneViewSet, basename='zones')
router.register(r'guest-sessions', GuestSessionViewSet, basename='guest-sessions')
router.register(r'orders', OrderViewSet, basename='orders')
router.register(r'order-items', OrderItemViewSet, basename='order-items')

# Payments
router.register(r'pre-auth-holds', PreAuthHoldViewSet, basename='pre-auth-holds')
router.register(r'transactions', TransactionViewSet, basename='transactions')
router.register(r'payment-configs', PaymentGatewayConfigViewSet, basename='payment-configs')

# Events and Tickets
router.register(r'events', EventViewSet, basename='events')
router.register(r'ticket-tiers', TicketTierViewSet, basename='ticket-tiers')
router.register(r'tickets', TicketViewSet, basename='tickets')

# Staff Attendance
router.register(r'staff-attendance', StaffAttendanceViewSet, basename='staff-attendance')

# Notifications
router.register(r'notifications', NotificationViewSet, basename='notifications')

# Users
router.register(r'users', UserViewSet, basename='users')

# =============================================================================
# URL Patterns
# =============================================================================
urlpatterns = [
    # Admin
    path('admin/', admin.site.urls),

    # API Router (venues, staff, tables, etc.)
    path('api/', include(router.urls)),

    # Explore app
    path('api/', include('explore.urls')),

    # Gate app
    path('api/', include('gate.urls')),

    # Notifications app
    path('api/', include('notifications.urls')),

    # Control app (Manager Dashboard + HQ Admin)
    path('api/', include('control.urls')),

    # HQ app (health, system-status, etc.)
    path('api/', include('hq.urls')),

    # Security app (NEW)
    path('api/security/', include('security.urls')),   # <-- ADDED

    # =========================================================================
    # Authentication Endpoints (from users app)
    # =========================================================================

    # Customer Registration
    path('api/auth/register-customer/',
         AuthViewSet.as_view({'post': 'register_customer'}),
         name='register_customer'),

    # Staff Login (Phone + PIN)
    path('api/auth/staff-login/',
         AuthViewSet.as_view({'post': 'staff_login'}),
         name='staff_login'),

    # Manager Login (Email + Password + 2FA)
    path('api/auth/manager-login/',
         AuthViewSet.as_view({'post': 'manager_login'}),
         name='manager_login'),

    # Admin Zero-Trust Login (Request Link)
    path('api/auth/admin-login-request/',
         AuthViewSet.as_view({'post': 'admin_login_request'}),
         name='admin_login_request'),

    # Admin Zero-Trust Login (Confirm with Token)
    path('api/auth/admin-login-confirm/',
         AuthViewSet.as_view({'post': 'admin_login_confirm'}),
         name='admin_login_confirm'),

    # OTP Endpoints
    path('api/auth/request-otp/',
         AuthViewSet.as_view({'post': 'request_otp'}),
         name='request_otp'),

    path('api/auth/verify-otp/',
         AuthViewSet.as_view({'post': 'verify_otp'}),
         name='verify_otp'),

    # Password Reset
    path('api/auth/password-reset-request/',
         AuthViewSet.as_view({'post': 'password_reset_request'}),
         name='password_reset_request'),

    path('api/auth/password-reset-confirm/',
         AuthViewSet.as_view({'post': 'password_reset_confirm'}),
         name='password_reset_confirm'),

    # Staff PIN Management
    path('api/auth/staff-set-pin/',
         AuthViewSet.as_view({'post': 'staff_set_pin'}),
         name='staff_set_pin'),

    path('api/auth/staff-change-pin/',
         AuthViewSet.as_view({'post': 'staff_change_pin'}),
         name='staff_change_pin'),

    path('api/auth/staff-reset-pin-request/',
         AuthViewSet.as_view({'post': 'staff_reset_pin_request'}),
         name='staff_reset_pin_request'),

    path('api/auth/staff-reset-pin-confirm/',
         AuthViewSet.as_view({'post': 'staff_reset_pin_confirm'}),
         name='staff_reset_pin_confirm'),

    # JWT Token (Alternative login)
    path('api/auth/token/',
         TokenObtainPairView.as_view(),
         name='token_obtain_pair'),

    path('api/auth/token/refresh/',
         TokenRefreshView.as_view(),
         name='token_refresh'),

    # Logout
    path('api/auth/logout/',
         AuthViewSet.as_view({'post': 'logout'}),
         name='logout'),

    # Refresh Token
    path('api/auth/refresh-token/',
         AuthViewSet.as_view({'post': 'refresh_token'}),
         name='refresh_token'),

    # User Profile
    path('api/auth/me/',
         UserViewSet.as_view({'get': 'me'}),
         name='user_profile'),

    # Browsable API
    path('api-auth/', include('rest_framework.urls')),

    # Redirect after login
    path('accounts/profile/',
         RedirectView.as_view(url='/api/', permanent=False)),
]