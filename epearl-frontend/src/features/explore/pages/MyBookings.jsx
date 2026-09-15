import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { exploreApi } from '../../../api/endpoints/explore';
import { format } from 'date-fns';
import { toast } from 'react-toastify';

const MyBookings = () => {
  const [bookings, setBookings] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchBookings = async () => {
      try {
        const response = await exploreApi.getBookings();
        setBookings(response.data);
      } catch (err) {
        setError(err.response?.data?.error || 'Failed to load bookings');
      } finally {
        setLoading(false);
      }
    };
    fetchBookings();
  }, []);

  const handleCancel = async (id) => {
    if (!confirm('Are you sure you want to cancel this booking?')) return;
    try {
      await exploreApi.cancelBooking(id);
      setBookings(bookings.filter(b => b.id !== id));
      toast.success('Booking cancelled');
    } catch (err) {
      toast.error('Failed to cancel booking');
    }
  };

  if (loading) return <div className="text-center py-8">Loading bookings...</div>;
  if (error) return <div className="text-red-500 text-center py-8">{error}</div>;
  if (bookings.length === 0) return <div className="text-center py-8 text-gray-500">No bookings found.</div>;

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">My Bookings</h1>
      <div className="space-y-4">
        {bookings.map((booking) => (
          <div key={booking.id} className="bg-white p-4 rounded-lg shadow-md flex flex-wrap items-center justify-between">
            <div>
              <h3 className="font-semibold text-lg">{booking.venue_name}</h3>
              <p className="text-gray-600 text-sm">
                {format(new Date(booking.booking_date), 'PPP')} at {booking.start_time} • {booking.party_size} guests
              </p>
              <p className="text-sm">
                Status: <span className={`font-medium ${booking.status === 'confirmed' ? 'text-green-600' : 'text-yellow-600'}`}>{booking.status}</span>
              </p>
            </div>
            <div className="flex gap-2 mt-2 sm:mt-0">
              <Link to={`/bookings/${booking.id}`} className="text-blue-600 hover:underline text-sm">View</Link>
              {booking.status === 'pending' && (
                <button onClick={() => handleCancel(booking.id)} className="text-red-600 hover:underline text-sm">Cancel</button>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default MyBookings;