# staff/services/qr_service.py

import qrcode
from io import BytesIO
import base64
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage


class QRService:
    """Service for generating QR codes for staff."""

    @staticmethod
    def generate_qr_image(data, size=10, border=4):
        """
        Generate a QR code image as base64 string.
        """
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=size,
            border=border,
        )
        qr.add_data(data)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        return base64.b64encode(buffer.getvalue()).decode()

    @staticmethod
    def get_staff_qr_base64(staff):
        """Get base64 QR image for a staff member."""
        qr_data = str(staff.staff_qr)
        return QRService.generate_qr_image(qr_data)