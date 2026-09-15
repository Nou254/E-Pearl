# venues/services/document_service.py

import os
from django.core.files.storage import default_storage
from django.utils import timezone
from rest_framework import serializers

class DocumentService:
    ALLOWED_DOCUMENT_TYPES = ['kra_pin_certificate', 'business_permit', 'certificate_of_incorporation']

    @staticmethod
    def validate_document_type(document_type):
        if document_type not in DocumentService.ALLOWED_DOCUMENT_TYPES:
            raise serializers.ValidationError(f"Invalid document type. Allowed: {', '.join(DocumentService.ALLOWED_DOCUMENT_TYPES)}")

    @staticmethod
    def upload_document(venue, document_type, uploaded_file):
        """
        Store the uploaded file and update the venue's documents field.
        Returns the saved file path.
        """
        DocumentService.validate_document_type(document_type)

        # Build a safe filename
        ext = os.path.splitext(uploaded_file.name)[1]
        filename = f"{venue.id}_{document_type}_{timezone.now().strftime('%Y%m%d%H%M%S')}{ext}"
        file_path = f"documents/{venue.id}/{filename}"

        # Save file using Django's storage
        saved_path = default_storage.save(file_path, uploaded_file)

        # Update venue documents JSON
        documents = venue.documents or {}
        documents[document_type] = saved_path
        venue.documents = documents
        venue.save(update_fields=['documents'])

        return saved_path

    @staticmethod
    def delete_document(venue, document_type):
        """Delete a previously uploaded document."""
        documents = venue.documents or {}
        if document_type in documents:
            file_path = documents[document_type]
            if default_storage.exists(file_path):
                default_storage.delete(file_path)
            del documents[document_type]
            venue.documents = documents
            venue.save(update_fields=['documents'])
            return True
        return False