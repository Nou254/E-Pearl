import React, { useEffect } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import api from '../../services/api'
import LoadingSpinner from '../../components/common/LoadingSpinner'
import { toast } from 'react-toastify'

const AdminLoginConfirm = () => {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const token = searchParams.get('token')

  useEffect(() => {
    const confirm = async () => {
      if (!token) {
        toast.error('Invalid or missing token')
        navigate('/auth/admin/login-request')
        return
      }
      try {
        const res = await api.post('/auth/admin-login-confirm/', { token })
        const { access, refresh } = res.data
        localStorage.setItem('accessToken', access)
        localStorage.setItem('refreshToken', refresh)
        toast.success('Login successful')
        navigate('/hq')
      } catch (err) {
        toast.error(err.response?.data?.detail || 'Login failed')
        navigate('/auth/admin/login-request')
      }
    }
    confirm()
  }, [token, navigate])

  return (
    <div className="min-h-screen flex items-center justify-center">
      <LoadingSpinner />
    </div>
  )
}

export default AdminLoginConfirm