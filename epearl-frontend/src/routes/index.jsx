import { Routes, Route } from 'react-router-dom'
import { ProtectedRoute } from '../components/auth/ProtectedRoute'

// Auth Pages
import CustomerLogin from '../pages/auth/CustomerLogin'
import CustomerSignup from '../pages/auth/CustomerSignup'
import PasswordResetRequest from '../pages/auth/PasswordResetRequest'
import PasswordResetConfirm from '../pages/auth/PasswordResetConfirm'
import OTPVerification from '../pages/auth/OTPVerification'
import StaffLogin from '../pages/auth/StaffLogin'
import StaffSetPin from '../pages/auth/StaffSetPin'
import StaffChangePin from '../pages/auth/StaffChangePin'
import StaffResetPinRequest from '../pages/auth/StaffResetPinRequest'
import StaffResetPinConfirm from '../pages/auth/StaffResetPinConfirm'
import ManagerLogin from '../pages/auth/ManagerLogin'
import Manager2FASetup from '../pages/auth/Manager2FASetup'
import Manager2FAVerify from '../pages/auth/Manager2FAVerify'
import AdminLoginRequest from '../pages/auth/AdminLoginRequest'
import AdminLoginConfirm from '../pages/auth/AdminLoginConfirm'
import Logout from '../pages/auth/Logout'

// Onboarding
import OnboardingWizard from '../pages/onboarding/OnboardingWizard'

// Placeholder pages (will be implemented later)
const Dashboard = () => <div>Dashboard</div>
const Control = () => <div>Control</div>
const HQ = () => <div>HQ</div>

export default function AppRoutes() {
  return (
    <Routes>
      {/* Public routes */}
      <Route path="/auth/login/customer" element={<CustomerLogin />} />
      <Route path="/auth/signup" element={<CustomerSignup />} />
      <Route path="/auth/password-reset" element={<PasswordResetRequest />} />
      <Route path="/auth/password-reset/confirm" element={<PasswordResetConfirm />} />
      <Route path="/auth/verify-otp" element={<OTPVerification />} />
      
      <Route path="/auth/staff/login" element={<StaffLogin />} />
      <Route path="/auth/staff/set-pin" element={<StaffSetPin />} />
      <Route path="/auth/staff/change-pin" element={<StaffChangePin />} />
      <Route path="/auth/staff/reset-pin" element={<StaffResetPinRequest />} />
      <Route path="/auth/staff/reset-pin/confirm" element={<StaffResetPinConfirm />} />

      <Route path="/auth/manager/login" element={<ManagerLogin />} />
      <Route path="/auth/manager/2fa-setup" element={<Manager2FASetup />} />
      <Route path="/auth/manager/2fa-verify" element={<Manager2FAVerify />} />

      <Route path="/auth/admin/login-request" element={<AdminLoginRequest />} />
      <Route path="/auth/admin/login-confirm" element={<AdminLoginConfirm />} />

      <Route path="/auth/logout" element={<Logout />} />

      {/* Onboarding (protected) */}
      <Route path="/onboarding" element={<ProtectedRoute><OnboardingWizard /></ProtectedRoute>} />

      {/* Protected routes */}
      <Route path="/" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
      <Route path="/control" element={<ProtectedRoute><Control /></ProtectedRoute>} />
      <Route path="/hq" element={<ProtectedRoute><HQ /></ProtectedRoute>} />
    </Routes>
  )
}