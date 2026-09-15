# staff/urls.py

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    StaffViewSet,
    ShiftViewSet,
    ShiftStaffViewSet,
    StaffAttendanceViewSet,
    StaffReportViewSet,
    StaffPermissionViewSet,      # NEW
    ShiftHandoverViewSet,        # NEW
    StaffPerformanceViewSet,     # NEW
)

router = DefaultRouter()

# Existing views
router.register(r'staff', StaffViewSet, basename='staff')
router.register(r'shifts', ShiftViewSet, basename='shifts')
router.register(r'shift-staff', ShiftStaffViewSet, basename='shift-staff')
router.register(r'staff-attendance', StaffAttendanceViewSet, basename='staff-attendance')
router.register(r'staff-reports', StaffReportViewSet, basename='staff-reports')

# New views – added after existing ones
router.register(r'staff-permissions', StaffPermissionViewSet, basename='staff-permissions')
router.register(r'shift-handovers', ShiftHandoverViewSet, basename='shift-handovers')
router.register(r'performance-metrics', StaffPerformanceViewSet, basename='performance-metrics')

urlpatterns = [
    path('', include(router.urls)),
]