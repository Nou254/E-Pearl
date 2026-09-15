# orders/serializers.py

from rest_framework import serializers
from .models import MenuCategory, MenuItem, Modifier, Order, OrderItem


class MenuCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = MenuCategory
        fields = [
            'id', 'venue', 'category_name', 'category_description',
            'display_order', 'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class MenuItemSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.category_name', read_only=True)

    class Meta:
        model = MenuItem
        fields = [
            'id', 'venue', 'category', 'category_name',
            'item_name', 'item_description', 'price', 'image_url',
            'item_type', 'is_active', 'is_available', 'display_order',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class ModifierSerializer(serializers.ModelSerializer):
    class Meta:
        model = Modifier
        fields = [
            'id', 'venue', 'menu_item', 'modifier_name',
            'modifier_options', 'is_required', 'is_active',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class OrderItemSerializer(serializers.ModelSerializer):
    item_name_display = serializers.CharField(source='item_name', read_only=True)

    class Meta:
        model = OrderItem
        fields = [
            'id', 'order', 'venue', 'menu_item', 'item_name',
            'item_name_display', 'item_type', 'quantity', 'unit_price',
            'total_price', 'modifiers', 'item_status', 'guest',
            'priority', 'reassigned_from_host', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class OrderItemUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = ['item_status']
        read_only_fields = ['id', 'created_at', 'updated_at']


class PriorityUpdateSerializer(serializers.Serializer):
    priority = serializers.IntegerField(min_value=0, max_value=100)


class ReassignItemSerializer(serializers.Serializer):
    """Serializer for reassigning an order item from host to a guest."""
    guest_session_id = serializers.UUIDField(help_text="The guest session to reassign this item to")

    def validate_guest_session_id(self, value):
        from guest_sessions.models import GuestSession
        if not GuestSession.objects.filter(id=value, status='active').exists():
            raise serializers.ValidationError("Invalid or inactive guest session.")
        return value


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    guest_session_id = serializers.UUIDField(source='guest_session.id', read_only=True)

    class Meta:
        model = Order
        fields = [
            'id', 'venue', 'guest_session', 'guest_session_id',
            'order_status', 'total_amount', 'order_time',
            'ready_time', 'served_time', 'served_by', 'table',
            'items', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class OrderCreateSerializer(serializers.ModelSerializer):
    items = serializers.ListField(
        child=serializers.DictField(),
        write_only=True,
        required=False,
        help_text="List of items with menu_item_id, quantity, modifiers"
    )

    class Meta:
        model = Order
        fields = ['guest_session', 'table', 'items']

    def create(self, validated_data):
        return validated_data