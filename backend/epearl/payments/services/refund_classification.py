# payments/services/refund_classification.py

class RefundClassification:
    """
    Classifies refund requests based on the reason and booking context.
    """
    VENUE_FAULT = 'venue_fault'
    NOU_FAULT = 'nou_fault'
    GATEWAY_ISSUE = 'gateway_issue'
    CUSTOMER_CANCELLATION = 'customer_cancellation'

    @classmethod
    def classify(cls, booking, reason):
        """
        Determine the classification of a refund request.
        """
        # If the venue cancelled the booking
        if booking.venue_cancelled:
            return cls.VENUE_FAULT

        # If the reason indicates technical error or double charge
        if reason in ['technical_issue', 'double_charge']:
            return cls.NOU_FAULT

        # If the reason indicates gateway problem (e.g., payment failed but funds deducted)
        if reason == 'gateway_error':
            return cls.GATEWAY_ISSUE

        # Default: customer cancellation
        return cls.CUSTOMER_CANCELLATION

    @classmethod
    def get_responsible_party(cls, classification):
        """
        Returns who is financially responsible for the refund.
        """
        mapping = {
            cls.VENUE_FAULT: 'venue',
            cls.NOU_FAULT: 'nou',
            cls.GATEWAY_ISSUE: 'gateway',
            cls.CUSTOMER_CANCELLATION: 'customer',
        }
        return mapping.get(classification, 'unknown')