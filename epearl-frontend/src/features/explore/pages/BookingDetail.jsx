import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { exploreApi } from '../../../api/endpoints/explore';
import { format } from 'date-fns';
import { toast } from 'react-toastify';

const BookingDetail = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const [booking, setBooking] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchDetail = async () => {
      try {
        const response = await exploreApi.getBookingDetail(id);
        setBooking(response.data);
      } catch (err) {
        setError(err.response?.data?.error || 'Failed to load booking');
      } finally {
        setLoading(false);
      }
    };
    fetchDetail();
  }, [id]);

  const handleCancel = async () => {
    if (!confirm('Cancel this booking?')) return;
    try {
      await exploreApi.cancelBooking(id);
      setBooking({ ...booking, status: 'cancelled' });
      toast.success('Booking cancelled');
    } catch (err) {
      toast.error('Failed to cancel booking');
    }
  };

  const handleCheckIn = async () => {
    try {
      await exploreApi.checkIn(id);
      setBooking({ ...booking, checked_in: true, status: 'checked_in' });
      toast.success('Checked in successfully');
    } catch (err) {
      toast.error('Check-in failed');
    }
  };

  const handleCheckOut = async () => {
    try {
      await exploreApi.checkOut(id);
      setBooking({ ...booking, checked_out: true, status: 'completed' });
      toast.success('Checked out successfully');
    } catch (err) {
      toast.error('Check-out failed');
    }
  };

  const handleRequestRefund = () => {
    navigate(`/bookings/${id}/refund`); // we can implement refund form later
  };

  if (loading) return <div className="text-center py-8">Loading...</div>;
  if (error) return <div className="text-red-500 text-center py-8">{error}</div>;
  if (!booking) return <div className="text-center py-8">Booking not found.</div>;

  return (
    <div className="max-w-2xl mx-auto bg-white rounded-lg shadow-md p-6">
      <h1 className="text-2xl font-bold mb-4">Booking Details</h1>
      <div className="space-y-3">
        <div><span className="font-medium">Venue:</span> {booking.venue_name}</div>
        <div><span className="font-medium">Date:</span> {format(new Date(booking.booking_date), 'PPP')}</div>
        <div><span className="font-medium">Time:</span> {booking.start_time}</div>
        <div><span className="font-medium">Guests:</span> {booking.party_size}</div>
        <div><span className="font-medium">Status:</span> <span className={`font-medium ${booking.status === 'confirmed' ? 'text-green-600' : 'text-yellow-600'}`}>{booking.status}</span></div>
        <div><span className="font-medium">Payment:</span> {booking.payment_status}</div>
        <div><span className="font-medium">Booking QR:</span> <code className="bg-gray-100 px-2 py-1 rounded">{booking.booking_qr}</code></div>
      </div>

      <div className="mt-6 flex flex-wrap gap-3">
        {booking.status === 'confirmed' && !booking.checked_in && (
          <button onClick={handleCheckIn} className="px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700">
            Check In
          </button>
        )}
        {booking.checked_in && !booking.checked_out && (
          <button onClick={handleCheckOut} className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700">
            Check Out
          </button>
        )}
        {booking.status === 'pending' && (
          <button onClick={handleCancel} className="px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700">
            Cancel Booking
          </button>
        )}
        {booking.payment_status === 'paid' && booking.status !== 'cancelled' && booking.refund_status === 'none' && (
          <button onClick={handleRequestRefund} className="px-4 py-2 bg-yellow-600 text-white rounded hover:bg-yellow-700">
            Request Refund
          </button>
        )}
      </div>
    </div>
  );
};

export default BookingDetail;