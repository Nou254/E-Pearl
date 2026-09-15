# control/tests.py

from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from venues.models import Venue
from control.models import PlatformAuditLog, VenueHealthMetrics, HQNotification, SupportTicket

User = get_user_model()


class ControlModelTests(TestCase):
    """Tests for Control models."""

    def setUp(self):
        self.admin = User.objects.create_superuser(
            email='ctrl_admin@test.com',
            password='adminpass123'
        )
        self.venue = Venue.objects.create(
            business_name='Control Test Venue',
            kra_pin='A123456789E',
            contact_phone='0722222222',
            contact_email='ctrl@venue.com',
            sub_domain='ctrl-venue'
        )

    def test_audit_log_creation(self):
        log = PlatformAuditLog.objects.create(
            actor=self.admin,
            action_type='venue_approve',
            target_model='Venue',
            target_id=str(self.venue.id),
            description='Approved venue documents'
        )
        self.assertEqual(log.action_type, 'venue_approve')
        self.assertIn('Control Test Venue', str(log))

    def test_health_metrics_creation(self):
        metrics = VenueHealthMetrics.objects.create(
            venue=self.venue,
            active_guests=10,
            occupied_tables=5,
            total_tables=20,
            revenue_today=5000.00
        )
        self.assertEqual(metrics.occupancy_rate(), 25.0)

    def test_hq_notification_creation(self):
        notification = HQNotification.objects.create(
            title='New Venue Registration',
            message='A new venue has registered',
            category='venue_registration',
            priority='high',
            venue=self.venue
        )
        self.assertFalse(notification.is_read)

    def test_support_ticket_creation(self):
        ticket = SupportTicket.objects.create(
            venue=self.venue,
            raised_by=self.admin,
            subject='Login Issue',
            description='Cannot login to the system',
            priority='high'
        )
        self.assertEqual(ticket.status, 'open')


class ControlAPITests(TestCase):
    """Tests for Control API endpoints."""

    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_superuser(
            email='ctrl_api_admin@test.com',
            password='adminpass123'
        )
        self.client.force_authenticate(user=self.admin)
        self.venue = Venue.objects.create(
            business_name='API Test Venue',
            kra_pin='A123456789F',
            contact_phone='0733333333',
            contact_email='api@venue.com',
            sub_domain='api-venue'
        )

    def test_dashboard_overview(self):
        response = self.client.get('/api/control-dashboard/overview/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('total_venues', response.data)
        self.assertIn('active_venues', response.data)
        self.assertIn('venues_by_tier', response.data)

    def test_audit_logs_list(self):
        PlatformAuditLog.objects.create(
            actor=self.admin,
            action_type='venue_approve',
            description='Test log'
        )
        response = self.client.get('/api/audit-logs/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_hq_notifications_list(self):
        HQNotification.objects.create(
            title='Test Notification',
            message='Test message',
            category='system_alert',
            priority='medium'
        )
        response = self.client.get('/api/hq-notifications/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_unread_count(self):
        HQNotification.objects.create(
            title='Unread',
            message='msg',
            category='system_alert',
            priority='low'
        )
        response = self.client.get('/api/hq-notifications/unread_count/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['unread_count'], 1)

    def test_support_tickets(self):
        SupportTicket.objects.create(
            venue=self.venue,
            raised_by=self.admin,
            subject='Test Ticket',
            description='Test description'
        )
        response = self.client.get('/api/support-tickets/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_unauthorized_access(self):
        self.client.force_authenticate(user=None)
        response = self.client.get('/api/control-dashboard/overview/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_non_admin_access(self):
        regular_user = User.objects.create_user(
            email='regular@test.com',
            phone='0744444444',
            password='testpass123',
            user_type='staff'
        )
        self.client.force_authenticate(user=regular_user)
        response = self.client.get('/api/control-dashboard/overview/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
