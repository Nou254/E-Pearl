// App.jsx

import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { Provider } from 'react-redux';
import { store } from './store';
import { ToastContainer } from 'react-toastify';
import 'react-toastify/dist/ReactToastify.css';

// =============================================================================
// Pages
// =============================================================================

// Auth
import Login from './features/auth/pages/Login';
import Register from './features/auth/pages/Register';
import ForgotPassword from './features/auth/pages/ForgotPassword';
import ResetPassword from './features/auth/pages/ResetPassword';

// Explore / Discovery
import ExploreFeed from './features/explore/pages/ExploreFeed';
import VenueProfile from './features/explore/pages/VenueProfile';
import MyBookings from './features/explore/pages/MyBookings';
import BookingDetail from './features/explore/pages/BookingDetail';
import BookingCheckout from './features/explore/pages/BookingCheckout';

// Events
import Events from './features/events/pages/Events';
import EventDetail from './features/events/pages/EventDetail';
import MyTickets from './features/events/pages/MyTickets';

// Guest / Host
import GuestDashboard from './features/guest/pages/GuestDashboard';
import HostDashboard from './features/host/pages/HostDashboard';

// Expenditure
import MyExpenditure from './features/expenditure/pages/MyExpenditure';

// Control (Venue Manager)
import ManagerDashboard from './features/control/pages/ManagerDashboard';
import StaffManagement from './features/control/pages/StaffManagement';
import MenuBuilder from './features/control/pages/MenuBuilder';
import FloorPlan from './features/control/pages/FloorPlan';
import AuditLog from './features/control/pages/AuditLog';
import RefundPolicy from './features/control/pages/RefundPolicy';
import PaymentConfig from './features/control/pages/PaymentConfig';
import OnboardingWizard from './features/control/pages/OnboardingWizard';

// HQ Admin
import HQDashboard from './features/hq/pages/HQDashboard';
import VenueManagement from './features/hq/pages/VenueManagement';
import RefundReview from './features/hq/pages/RefundReview';
import TrialManagement from './features/hq/pages/TrialManagement';
import SystemHealth from './features/hq/pages/SystemHealth';

// QR Scan
import QRScan from './features/scan/pages/QRScan';

// =============================================================================
// Components
// =============================================================================
import Navbar from './components/Navbar';
import ProtectedRoute from './components/ProtectedRoute';
import AdminRoute from './components/AdminRoute';
import ManagerRoute from './components/ManagerRoute';
import Layout from './components/Layout';

// =============================================================================
// Main App
// =============================================================================
function App() {
  return (
    <Provider store={store}>
      <Router>
        <div className="min-h-screen bg-gray-50">
          <ToastContainer
            position="top-right"
            autoClose={5000}
            hideProgressBar={false}
            newestOnTop
            closeOnClick
            rtl={false}
            pauseOnFocusLoss
            draggable
            pauseOnHover
            theme="light"
          />

          <Navbar />

          <main className="container mx-auto px-4 py-8">
            <Routes>
              {/* Public Routes */}
              <Route path="/" element={<ExploreFeed />} />
              <Route path="/venue/:id" element={<VenueProfile />} />
              <Route path="/events" element={<Events />} />
              <Route path="/events/:id" element={<EventDetail />} />
              <Route path="/scan" element={<QRScan />} />

              {/* Auth Routes */}
              <Route path="/login" element={<Login />} />
              <Route path="/register" element={<Register />} />
              <Route path="/forgot-password" element={<ForgotPassword />} />
              <Route path="/reset-password/:token" element={<ResetPassword />} />

              {/* Guest Routes (authenticated) */}
              <Route element={<ProtectedRoute />}>
                <Route path="/guest/dashboard" element={<GuestDashboard />} />
                <Route path="/bookings" element={<MyBookings />} />
                <Route path="/bookings/:id" element={<BookingDetail />} />
                <Route path="/bookings/checkout" element={<BookingCheckout />} />
                <Route path="/tickets" element={<MyTickets />} />
                <Route path="/expenditure" element={<MyExpenditure />} />
              </Route>

              {/* Host Routes */}
              <Route element={<ProtectedRoute />}>
                <Route path="/host/dashboard" element={<HostDashboard />} />
              </Route>

              {/* Manager Routes */}
              <Route element={<ManagerRoute />}>
                <Route path="/control/dashboard" element={<ManagerDashboard />} />
                <Route path="/control/onboarding" element={<OnboardingWizard />} />
                <Route path="/control/staff" element={<StaffManagement />} />
                <Route path="/control/menu" element={<MenuBuilder />} />
                <Route path="/control/floor-plan" element={<FloorPlan />} />
                <Route path="/control/audit" element={<AuditLog />} />
                <Route path="/control/refund-policy" element={<RefundPolicy />} />
                <Route path="/control/payments" element={<PaymentConfig />} />
              </Route>

              {/* HQ Admin Routes */}
              <Route element={<AdminRoute />}>
                <Route path="/hq/dashboard" element={<HQDashboard />} />
                <Route path="/hq/venues" element={<VenueManagement />} />
                <Route path="/hq/refunds" element={<RefundReview />} />
                <Route path="/hq/trials" element={<TrialManagement />} />
                <Route path="/hq/health" element={<SystemHealth />} />
              </Route>

              {/* Catch-all */}
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </main>
        </div>
      </Router>
    </Provider>
  );
}

export default App;