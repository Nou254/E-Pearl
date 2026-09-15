import React from 'react'
import { useForm, FormProvider } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { staffLoginSchema } from '../../utils/validators'
import api from '../../services/api'
import AuthLayout from '../../components/auth/AuthLayout'
import Input from '../../components/common/Input'
import Button from '../../components/common/Button'
import { toast } from 'react-toastify'

const StaffLogin = () => {
  const methods = useForm({ resolver: zodResolver(staffLoginSchema) })
  const { handleSubmit, formState: { isSubmitting } } = methods

  const onSubmit = async (data) => {
    try {
      const res = await api.post('/auth/staff-login/', data)
      localStorage.setItem('accessToken', res.data.access)
      localStorage.setItem('refreshToken', res.data.refresh)
      window.location.href = '/'
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Login failed')
    }
  }

  return (
    <AuthLayout title="Staff Login" subtitle="Enter your phone and PIN">
      <FormProvider {...methods}>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <Input name="phone" label="Phone" placeholder="e.g., 254700000000" required />
          <Input name="pin" label="PIN" type="password" placeholder="4-digit PIN" required maxLength={4} />
          <Button type="submit" disabled={isSubmitting} fullWidth>
            {isSubmitting ? 'Logging in...' : 'Sign In'}
          </Button>
        </form>
      </FormProvider>
    </AuthLayout>
  )
}

export default StaffLogin