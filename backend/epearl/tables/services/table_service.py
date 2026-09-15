# tables/services/table_service.py

from django.core.exceptions import ValidationError
from django.utils import timezone
from ..models import Table, Zone
from venues.services.tier_service import TierService
import qrcode
from io import BytesIO
import base64


class TableService:
    """Service for table-related operations."""

    @staticmethod
    def create_table(venue, validated_data):
        """
        Create a new table with tier enforcement and QR generation.
        """
        # Check tier limits
        if not TierService.can_add_table(venue):
            raise ValidationError(
                f"You have reached the maximum number of tables allowed for your {venue.subscription_tier} tier. "
                "Please upgrade to add more tables."
            )

        # Ensure zone belongs to this venue
        zone = validated_data.get('zone')
        if zone and zone.venue != venue:
            raise ValidationError("Zone does not belong to this venue.")

        # Create the table
        table = Table.objects.create(
            venue=venue,
            qr_code_label=validated_data.get('qr_code_label', f"Table {validated_data.get('table_number')}"),
            **validated_data
        )
        return table

    @staticmethod
    def update_table(table, validated_data):
        """Update table details with validation."""
        # Ensure zone belongs to same venue
        zone = validated_data.get('zone')
        if zone and zone.venue != table.venue:
            raise ValidationError("Zone does not belong to this venue.")

        for attr, value in validated_data.items():
            setattr(table, attr, value)
        table.save()
        return table

    @staticmethod
    def get_qr_code_base64(table):
        """Generate a QR code image for the table as base64."""
        # Use the table's UUID as QR content
        qr_data = str(table.qr_code)

        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(qr_data)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        return base64.b64encode(buffer.getvalue()).decode()

    @staticmethod
    def get_available_tables(venue, zone_id=None, min_capacity=1):
        """Get all available tables with optional filtering."""
        queryset = Table.objects.filter(venue=venue, is_active=True, status='available')
        if zone_id:
            queryset = queryset.filter(zone_id=zone_id)
        if min_capacity > 1:
            queryset = queryset.filter(max_capacity__gte=min_capacity)
        return queryset

    @staticmethod
    def occupy_table(table, headcount=1):
        """Mark a table as occupied with the given headcount."""
        if not table.is_available():
            raise ValidationError("Table is not available.")
        if headcount > table.max_capacity:
            raise ValidationError(f"Table can only seat {table.max_capacity} people.")
        table.occupy(headcount)
        return table

    @staticmethod
    def free_table(table):
        """Free an occupied table."""
        if table.status != 'occupied':
            raise ValidationError("Table is not occupied.")
        table.free()
        return table