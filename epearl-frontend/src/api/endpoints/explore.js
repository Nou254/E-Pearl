import client from '../client';

export const exploreApi = {
  // Public endpoints (no auth)
  getVenues: (params) => client.get('/public/explore/venues/', { params }),
  getVenueDetail: (id) => client.get(`/public/explore/venue-detail/${id}/`),

  // Authenticated endpoints for menu and bookings
  getPublicMenu: (venueId) => client.get('/menu-items/public-menu/', { params: { venue: venueId } }),
  getEvents: (venueId) => client.get('/events/', { params: { venue: venueId } }),

  // Bookings
  createBooking: (data) => client.post('/bookings/', data),
  getBookings: () => client.get('/bookings/'),
  getBookingDetail: (id) => client.get(`/bookings/${id}/`),
  cancelBooking: (id) => client.post(`/bookings/${id}/cancel/`),
  confirmBooking: (id) => client.post(`/bookings/${id}/confirm-booking/`),
  checkIn: (id) => client.post(`/bookings/${id}/check-in/`),
  checkOut: (id) => client.post(`/bookings/${id}/check-out/`),
  requestRefund: (id, data) => client.post(`/bookings/${id}/request-refund/`, data),
};