# explore/urls.py

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    BookingViewSet,
    RoomTypeViewSet,
    RoomAvailabilityViewSet,
    VenueHiringViewSet,
    PublicExploreViewSet,
    RatingViewSet,
)

router = DefaultRouter()
router.register(r'bookings', BookingViewSet, basename='bookings')
router.register(r'room-types', RoomTypeViewSet, basename='room-types')
router.register(r'room-availability', RoomAvailabilityViewSet, basename='room-availability')
router.register(r'venue-hiring', VenueHiringViewSet, basename='venue-hiring')
router.register(r'public/explore', PublicExploreViewSet, basename='public-explore')
router.register(r'ratings', RatingViewSet, basename='ratings')

urlpatterns = [
    path('', include(router.urls)),
]