import React, { useEffect, useState } from 'react'
import api from '../../services/api'
import AuthLayout from '../../components/auth/AuthLayout'
import Button from '../../components/common/Button'
import { toast } from 'react-toastify'
import { useNavigate } from 'react-router-dom'

const Manager2FASetup = () => {
  const navigate = useNavigate()
  const [qrCode, setQrCode] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const fetchQR = async () => {
      try {
        const { data } = await api.get('/auth/2fa/setup/')
        setQrCode(data.qr_code)
        setLoading(false)
      } catch (err) {
        toast.error('Failed to load 2FA setup')
        setLoading(false)
      }
    }
    fetchQR()
  }, [])

  const handleDone = () => {
    navigate('/auth/manager/2fa-verify')
  }

  return (
    <AuthLayout title="2FA Setup" subtitle="Scan the QR code with Google Authenticator">
      {loading ? (
        <p>Loading...</p>
      ) : (
        <div className="space-y-4 text-center">
          {qrCode && <img src={qrCode} alt="QR Code" className="mx-auto" />}
          <p className="text-sm text-gray-600">Scan this QR code with your authenticator app, then click below to verify.</p>
          <Button onClick={handleDone} fullWidth>I've Scanned the Code</Button>
        </div>
      )}
    </AuthLayout>
  )
}

export default Manager2FASetup