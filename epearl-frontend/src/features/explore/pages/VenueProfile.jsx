import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useDispatch, useSelector } from 'react-redux';
import { fetchVenueDetail, fetchPublicMenu, fetchEvents, clearSelectedVenue } from '../store/exploreSlice';
import BookingModal from '../components/BookingModal';
import { format } from 'date-fns';

const VenueProfile = () => {
  const { id } = useParams();
  const dispatch = useDispatch();
  const navigate = useNavigate();
  const { selectedVenue, publicMenu, events, loading, error } = useSelector((state) => state.explore);
  const isAuthenticated = useSelector((state) => state.auth.isAuthenticated);
  const [showBookingModal, setShowBookingModal] = useState(false);
  const [activeTab, setActiveTab] = useState('info');

  useEffect(() => {
    dispatch(fetchVenueDetail(id));
    dispatch(fetchPublicMenu(id));
    dispatch(fetchEvents(id));
    return () => {
      dispatch(clearSelectedVenue());
    };
  }, [dispatch, id]);

  const handleBooking = () => {
    if (!isAuthenticated) {
      navigate('/login', { state: { from: `/venue/${id}` } });
      return;
    }
    setShowBookingModal(true);
  };

  if (loading) return <div className="text-center py-8">Loading venue details...</div>;
  if (error) return <div className="text-red-500 text-center py-8">Error loading venue: {error}</div>;
  if (!selectedVenue) return <div className="text-center py-8">Venue not found.</div>;

  return (
    <div className="max-w-4xl mx-auto">
      <div className="bg-white rounded-lg shadow-md overflow-hidden">
        <img
          src={selectedVenue.cover_image_url || 'https://via.placeholder.com/1200x400?text=Venue+Cover'}
          alt={selectedVenue.business_name}
          className="w-full h-64 object-cover"
        />
        <div className="p-6">
          <div className="flex justify-between items-start">
            <div>
              <h1 className="text-3xl font-bold text-gray-800">{selectedVenue.business_name}</h1>
              <p className="text-gray-600 mt-1">{selectedVenue.description}</p>
              <div className="flex flex-wrap gap-4 mt-2 text-sm text-gray-500">
                <span> {selectedVenue.contact_phone}</span>
                <span> {selectedVenue.contact_email}</span>
                <span> {selectedVenue.physical_address}</span>
              </div>
            </div>
            <button
              onClick={handleBooking}
              className="px-6 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
            >
              Book Now
            </button>
          </div>

          {/* Tabs */}
          <div className="border-b border-gray-200 mt-6">
            <nav className="flex -mb-px">
              {['info', 'menu', 'events'].map((tab) => (
                <button
                  key={tab}
                  onClick={() => setActiveTab(tab)}
                  className={`py-2 px-4 text-sm font-medium ${
                    activeTab === tab
                      ? 'border-b-2 border-blue-500 text-blue-600'
                      : 'text-gray-500 hover:text-gray-700 hover:border-gray-300'
                  }`}
                >
                  {tab.charAt(0).toUpperCase() + tab.slice(1)}
                </button>
              ))}
            </nav>
          </div>

          {/* Tab content */}
          <div className="mt-4">
            {activeTab === 'info' && (
              <div>
                <h3 className="text-lg font-semibold">About</h3>
                <p className="text-gray-700 mt-2">{selectedVenue.description}</p>
                {selectedVenue.operating_hours && (
                  <div className="mt-4">
                    <h4 className="font-medium">Operating Hours</h4>
                    <pre className="text-sm text-gray-600 bg-gray-50 p-3 rounded">
                      {JSON.stringify(selectedVenue.operating_hours, null, 2)}
                    </pre>
                  </div>
                )}
                <div className="mt-4">
                  <h4 className="font-medium">Available Tables</h4>
                  <p className="text-gray-700">{selectedVenue.available_tables || 'N/A'}</p>
                </div>
                {selectedVenue.hiring_available && (
                  <div className="mt-2">
                    <span className="inline-block bg-green-100 text-green-800 text-xs font-semibold px-2 py-1 rounded">
                      Venue Hire Available
                    </span>
                  </div>
                )}
              </div>
            )}

            {activeTab === 'menu' && (
              <div>
                <h3 className="text-lg font-semibold mb-2">Menu</h3>
                {publicMenu.length === 0 ? (
                  <p className="text-gray-500">No menu items available.</p>
                ) : (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {publicMenu.map((item) => (
                      <div key={item.id} className="border rounded-lg p-3 flex justify-between items-start">
                        <div>
                          <h4 className="font-medium">{item.name}</h4>
                          <p className="text-sm text-gray-600">{item.description}</p>
                          <span className="text-sm font-semibold text-blue-600">KES {item.price}</span>
                        </div>
                        {item.image_url && (
                          <img src={item.image_url} alt={item.name} className="w-16 h-16 object-cover rounded" />
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {activeTab === 'events' && (
              <div>
                <h3 className="text-lg font-semibold mb-2">Upcoming Events</h3>
                {events.length === 0 ? (
                  <p className="text-gray-500">No upcoming events.</p>
                ) : (
                  <div className="space-y-4">
                    {events.map((event) => (
                      <div key={event.id} className="border rounded-lg p-4">
                        <h4 className="font-semibold">{event.event_name}</h4>
                        <p className="text-sm text-gray-600">{event.event_description}</p>
                        <div className="flex justify-between items-center mt-2 text-sm">
                          <span>{format(new Date(event.event_date), 'PPP')} at {event.event_start_time}</span>
                          <span className="text-blue-600">Tickets: {event.tickets_available || 'N/A'}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>

      {showBookingModal && (
        <BookingModal
          venue={selectedVenue}
          onClose={() => setShowBookingModal(false)}
          onSuccess={() => {
            setShowBookingModal(false);
            navigate('/bookings');
          }}
        />
      )}
    </div>
  );
};

export default VenueProfile;