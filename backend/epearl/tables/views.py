# tables/views.py

from rest_framework import viewsets, permissions, status, filters
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db import IntegrityError
from .models import Zone, Table
from .serializers import ZoneSerializer, TableSerializer, TableCreateSerializer, TableUpdateSerializer
from .services.table_service import TableService


class ZoneViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing zones within a venue.
    Only managers and owners can create/update/delete zones.
    """
    serializer_class = ZoneSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.user_type in ['admin', 'support']:
            return Zone.objects.all()
        if user.venue:
            return Zone.objects.filter(venue=user.venue, is_active=True)
        return Zone.objects.none()

    def perform_create(self, serializer):
        user = self.request.user
        if not user.venue:
            raise PermissionError("You are not associated with a venue.")
        serializer.save(venue=user.venue)


class TableViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing tables within a venue.
    Includes tier enforcement and QR code generation.
    """
    serializer_class = TableSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'zone', 'table_type', 'is_active']
    search_fields = ['table_number', 'qr_code_label']
    ordering_fields = ['table_number', 'created_at', 'max_capacity']
    ordering = ['table_number']

    def get_queryset(self):
        user = self.request.user
        if user.user_type in ['admin', 'support']:
            return Table.objects.all()
        if user.venue:
            return Table.objects.filter(venue=user.venue)
        return Table.objects.none()

    def get_serializer_class(self):
        if self.action == 'create':
            return TableCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return TableUpdateSerializer
        return TableSerializer

    def perform_create(self, serializer):
        user = self.request.user
        if not user.venue:
            raise PermissionError("You are not associated with a venue.")

        try:
            table = TableService.create_table(user.venue, serializer.validated_data)
            serializer.instance = table
        except IntegrityError as e:
            raise ValidationError(f"Table with this number already exists: {e}")

    def perform_update(self, serializer):
        table = self.get_object()
        try:
            TableService.update_table(table, serializer.validated_data)
            serializer.instance = table
        except IntegrityError as e:
            raise ValidationError(f"Table number already exists: {e}")

    @action(detail=True, methods=['get'])
    def qr_code(self, request, pk=None):
        """
        Get the QR code for a specific table as a base64 image.
        """
        table = self.get_object()
        qr_base64 = TableService.get_qr_code_base64(table)
        return Response({
            'table_id': table.id,
            'table_number': table.table_number,
            'qr_code': qr_base64
        })

    @action(detail=False, methods=['get'])
    def available(self, request):
        """
        Get all available tables for the current venue.
        Optional: filter by zone_id and min_capacity.
        """
        user = request.user
        if not user.venue:
            return Response({'error': 'You are not associated with a venue.'}, status=400)

        zone_id = request.query_params.get('zone_id')
        min_capacity = int(request.query_params.get('min_capacity', 1))

        tables = TableService.get_available_tables(user.venue, zone_id, min_capacity)
        serializer = self.get_serializer(tables, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def occupy(self, request, pk=None):
        """
        Mark a table as occupied with a given headcount.
        """
        table = self.get_object()
        headcount = request.data.get('headcount', 1)

        try:
            TableService.occupy_table(table, headcount)
            return Response({
                'status': 'occupied',
                'headcount': table.current_headcount,
                'message': f'Table {table.table_number} marked as occupied with {headcount} guests.'
            })
        except ValidationError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def free(self, request, pk=None):
        """
        Mark a table as free (available).
        """
        table = self.get_object()
        try:
            TableService.free_table(table)
            return Response({
                'status': 'available',
                'message': f'Table {table.table_number} is now available.'
            })
        except ValidationError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)