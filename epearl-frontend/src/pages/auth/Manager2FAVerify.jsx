import React, { useState } from 'react'
import api from '../../services/api'
import AuthLayout from '../../components/auth/AuthLayout'
import OTPInput from '../../components/common/OTPInput'
import Button from '../../components/common/Button'
import { toast } from 'react-toastify'
import { useNavigate } from 'react-router-dom'

const Manager2FAVerify = () => {
  const navigate = useNavigate()
  const [otp, setOtp] = useState('')
  const [loading, setLoading] = useState(false)

  const handleVerify = async () => {
    if (otp.length !== 6) return
    setLoading(true)
    try {
      const res = await api.post('/auth/verify-otp/', { otp })
      const { access, refresh } = res.data
      localStorage.setItem('accessToken', access)
      localStorage.setItem('refreshToken', refresh)
      window.location.href = '/control'
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Invalid OTP')
    } finally {
      setLoading(false)
    }
  }

  return (
    <AuthLayout title="2FA Verification" subtitle="Enter the 6-digit code from your authenticator app">
      <div className="space-y-6">
        <OTPInput length={6} onComplete={setOtp} disabled={loading} />
        <Button onClick={handleVerify} disabled={loading || otp.length !== 6} fullWidth>
          {loading ? 'Verifying...' : 'Verify'}
        </Button>
      </div>
    </AuthLayout>
  )
}

export default Manager2FAVerify