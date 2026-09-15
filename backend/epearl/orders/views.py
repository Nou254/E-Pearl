# orders/views.py

from rest_framework import viewsets, permissions, status, filters
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.decorators import action
from rest_framework.response import Response
from django.core.exceptions import ValidationError
from .models import MenuCategory, MenuItem, Modifier, Order, OrderItem
from .serializers import (
    MenuCategorySerializer,
    MenuItemSerializer,
    ModifierSerializer,
    OrderSerializer,
    OrderItemSerializer,
    OrderCreateSerializer,
    OrderItemUpdateSerializer,
    PriorityUpdateSerializer,
    ReassignItemSerializer,
)
from .services.order_service import OrderService
from venues.services.tier_service import TierService
from core.websocket_utils import notify_kitchen, notify_bar, notify_waiter
from notifications.services.notification_service import NotificationService
from control.services.inventory_service import InventoryService
import logging

logger = logging.getLogger(__name__)


class MenuCategoryViewSet(viewsets.ModelViewSet):
    serializer_class = MenuCategorySerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['is_active']
    search_fields = ['category_name']
    ordering_fields = ['display_order', 'category_name']

    def get_queryset(self):
        user = self.request.user
        if user.user_type in ['admin', 'support']:
            return MenuCategory.objects.all()
        if user.venue:
            return MenuCategory.objects.filter(venue=user.venue)
        return MenuCategory.objects.none()

    def perform_create(self, serializer):
        user = self.request.user
        if not user.venue:
            raise PermissionError("You are not associated with a venue.")
        serializer.save(venue=user.venue)


class MenuItemViewSet(viewsets.ModelViewSet):
    serializer_class = MenuItemSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['category', 'item_type', 'is_active', 'is_available']
    search_fields = ['item_name', 'item_description']
    ordering_fields = ['display_order', 'item_name', 'price']

    def get_queryset(self):
        user = self.request.user
        if user.user_type in ['admin', 'support']:
            return MenuItem.objects.all()
        if user.venue:
            return MenuItem.objects.filter(venue=user.venue)
        return MenuItem.objects.none()

    def perform_create(self, serializer):
        user = self.request.user
        if not user.venue:
            raise PermissionError("You are not associated with a venue.")
        serializer.save(venue=user.venue)


class ModifierViewSet(viewsets.ModelViewSet):
    serializer_class = ModifierSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['menu_item', 'is_active', 'is_required']

    def get_queryset(self):
        user = self.request.user
        if user.user_type in ['admin', 'support']:
            return Modifier.objects.all()
        if user.venue:
            return Modifier.objects.filter(venue=user.venue)
        return Modifier.objects.none()

    def perform_create(self, serializer):
        user = self.request.user
        if not user.venue:
            raise PermissionError("You are not associated with a venue.")
        serializer.save(venue=user.venue)


class OrderViewSet(viewsets.ModelViewSet):
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['order_status', 'table', 'guest_session']
    search_fields = ['guest_session__user__full_name']
    ordering_fields = ['order_time', 'total_amount']

    def get_queryset(self):
        user = self.request.user
        if user.user_type in ['admin', 'support']:
            return Order.objects.all()
        if user.venue:
            return Order.objects.filter(venue=user.venue)
        return Order.objects.filter(guest_session__user=user)

    def get_serializer_class(self):
        if self.action == 'create':
            return OrderCreateSerializer
        return OrderSerializer

    def perform_create(self, serializer):
        user = self.request.user
        if not user.venue:
            raise PermissionError("You are not associated with a venue.")

        order = OrderService.create_order(
            guest_session=serializer.validated_data['guest_session'],
            table=serializer.validated_data.get('table'),
            items_data=serializer.validated_data.get('items', [])
        )
        serializer.instance = order

        venue_id = str(user.venue.id)

        food_items = order.items.filter(item_type='food')
        if food_items.exists():
            notify_kitchen(venue_id, 'order.new', {
                'order_id': str(order.id),
                'table_number': order.table.table_number if order.table else 'Unknown',
                'items': [{'name': item.item_name, 'quantity': item.quantity} for item in food_items],
            })

        beverage_items = order.items.filter(item_type='beverage')
        if beverage_items.exists():
            notify_bar(venue_id, 'order.new', {
                'order_id': str(order.id),
                'table_number': order.table.table_number if order.table else 'Unknown',
                'items': [{'name': item.item_name, 'quantity': item.quantity} for item in beverage_items],
            })

        if order.table and order.table.assigned_waiter:
            notify_waiter(str(order.table.assigned_waiter.user.id), 'order.new', {
                'order_id': str(order.id),
                'table_number': order.table.table_number,
                'items': [{'name': item.item_name, 'quantity': item.quantity} for item in order.items.all()],
            })

    @action(detail=True, methods=['post'])
    def add_item(self, request, pk=None):
        order = self.get_object()
        menu_item_id = request.data.get('menu_item_id')
        quantity = request.data.get('quantity', 1)
        modifiers = request.data.get('modifiers', [])

        try:
            order_item = OrderService.add_item_to_order(
                order, menu_item_id, quantity, modifiers
            )
            return Response(
                OrderItemSerializer(order_item).data,
                status=status.HTTP_201_CREATED
            )
        except ValidationError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        order = self.get_object()
        try:
            OrderService.cancel_order(order)
            return Response({'status': 'cancelled'})
        except ValidationError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def approve_order(self, request, pk=None):
        order = self.get_object()
        if order.order_status != 'pending':
            return Response({'error': 'Order is not pending approval.'}, status=status.HTTP_400_BAD_REQUEST)

        for item in order.items.all():
            if item.menu_item:
                try:
                    InventoryService.deplete_stock(item.menu_item.id, item.quantity)
                except ValidationError as e:
                    return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        order.order_status = 'in_progress'
        order.save()

        venue_id = str(order.venue.id)
        food_items = order.items.filter(item_type='food')
        if food_items.exists():
            notify_kitchen(venue_id, 'order.approved', {
                'order_id': str(order.id),
                'table_number': order.table.table_number if order.table else 'Unknown',
                'items': [{'name': item.item_name, 'quantity': item.quantity} for item in food_items],
            })
        beverage_items = order.items.filter(item_type='beverage')
        if beverage_items.exists():
            notify_bar(venue_id, 'order.approved', {
                'order_id': str(order.id),
                'table_number': order.table.table_number if order.table else 'Unknown',
                'items': [{'name': item.item_name, 'quantity': item.quantity} for item in beverage_items],
            })

        return Response({'status': 'approved'})


class OrderItemViewSet(viewsets.ModelViewSet):
    serializer_class = OrderItemSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.user_type in ['admin', 'support']:
            return OrderItem.objects.all()
        if user.venue:
            return OrderItem.objects.filter(venue=user.venue)
        return OrderItem.objects.filter(order__guest_session__user=user)

    def get_serializer_class(self):
        if self.action in ['update', 'partial_update']:
            return OrderItemUpdateSerializer
        return OrderItemSerializer

    @action(detail=True, methods=['post'])
    def mark_ready(self, request, pk=None):
        order_item = self.get_object()
        try:
            OrderService.mark_ready(order_item)
            if order_item.order.table and order_item.order.table.assigned_waiter:
                notify_waiter(str(order_item.order.table.assigned_waiter.user.id), 'order.ready', {
                    'order_id': str(order_item.order.id),
                    'order_item_id': str(order_item.id),
                    'item_name': order_item.item_name,
                    'table_number': order_item.order.table.table_number,
                })
                waiter_user = order_item.order.table.assigned_waiter.user
                NotificationService.send_order_ready(order_item.order, waiter_user)
            return Response({'status': 'ready'})
        except ValidationError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def mark_served(self, request, pk=None):
        order_item = self.get_object()
        try:
            OrderService.update_item_status(order_item, 'served')
            return Response({'status': 'served'})
        except ValidationError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def fire(self, request, pk=None):
        order_item = self.get_object()
        serializer = PriorityUpdateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        increment = serializer.validated_data.get('priority', 10)
        try:
            updated_item = OrderService.fire_item(order_item, increment)
            return Response({
                'status': 'fired',
                'priority': updated_item.priority,
                'item_id': str(updated_item.id),
            })
        except ValidationError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def hold(self, request, pk=None):
        order_item = self.get_object()
        serializer = PriorityUpdateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        decrement = serializer.validated_data.get('priority', 10)
        try:
            updated_item = OrderService.hold_item(order_item, decrement)
            return Response({
                'status': 'held',
                'priority': updated_item.priority,
                'item_id': str(updated_item.id),
            })
        except ValidationError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    # NEW: Reassign to Guest
    @action(detail=True, methods=['post'])
    def reassign_to_guest(self, request, pk=None):
        """
        Reassign an order item from the host's order to a specific guest (self‑pay).
        Payload: {"guest_session_id": "uuid"}
        """
        order_item = self.get_object()
        serializer = ReassignItemSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        target_guest_session_id = serializer.validated_data['guest_session_id']

        # Ensure the user has permission: host or manager/owner
        user = request.user
        host_session = order_item.order.guest_session
        is_host = (user == host_session.user) if host_session.user else False
        is_manager = user.user_type in ['manager', 'owner'] if user.is_authenticated else False

        if not (is_host or is_manager):
            return Response(
                {'error': 'Only the host or a manager can reassign items.'},
                status=status.HTTP_403_FORBIDDEN
            )

        from guest_sessions.models import GuestSession
        try:
            target_guest_session = GuestSession.objects.get(id=target_guest_session_id, status='active')
        except GuestSession.DoesNotExist:
            return Response({'error': 'Invalid guest session.'}, status=status.HTTP_404_NOT_FOUND)

        # Ensure target is not the host
        if target_guest_session == host_session:
            return Response({'error': 'Cannot reassign to the host themselves.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            new_item = OrderService.reassign_item_to_guest(order_item, target_guest_session)
            return Response({
                'status': 'reassigned',
                'new_item_id': str(new_item.id),
                'guest_session_id': str(target_guest_session.id),
                'message': f"Item reassigned to guest {target_guest_session.id}"
            })
        except ValidationError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)