import React, { useState } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import api from '../../services/api'
import AuthLayout from '../../components/auth/AuthLayout'
import OTPInput from '../../components/common/OTPInput'
import Button from '../../components/common/Button'
import { toast } from 'react-toastify'

const OTPVerification = () => {
  const navigate = useNavigate()
  const location = useLocation()
  const [otp, setOtp] = useState('')
  const [loading, setLoading] = useState(false)
  const purpose = new URLSearchParams(location.search).get('purpose') || 'verify'

  const handleVerify = async () => {
    if (otp.length !== 6) return
    setLoading(true)
    try {
      await api.post('/auth/verify-otp/', { otp })
      toast.success('OTP verified')
      if (purpose === 'login') navigate('/')
      else navigate('/auth/login/customer')
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Invalid OTP')
    } finally {
      setLoading(false)
    }
  }

  return (
    <AuthLayout title="Verify OTP" subtitle="Enter the 6-digit code sent to your device">
      <div className="space-y-6">
        <OTPInput length={6} onComplete={setOtp} disabled={loading} />
        <Button onClick={handleVerify} disabled={loading || otp.length !== 6} fullWidth>
          {loading ? 'Verifying...' : 'Verify'}
        </Button>
      </div>
    </AuthLayout>
  )
}

export default OTPVerification