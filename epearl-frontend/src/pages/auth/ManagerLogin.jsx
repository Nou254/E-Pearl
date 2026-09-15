import React from 'react'
import { useForm, FormProvider } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { managerLoginSchema } from '../../utils/validators'
import api from '../../services/api'
import AuthLayout from '../../components/auth/AuthLayout'
import Input from '../../components/common/Input'
import Button from '../../components/common/Button'
import { toast } from 'react-toastify'
import { useNavigate } from 'react-router-dom'

const ManagerLogin = () => {
  const navigate = useNavigate()
  const methods = useForm({ resolver: zodResolver(managerLoginSchema) })
  const { handleSubmit, formState: { isSubmitting } } = methods

  const onSubmit = async (data) => {
    try {
      const res = await api.post('/auth/manager-login/', data)
      if (res.data.requires_2fa) {
        localStorage.setItem('manager_temp_token', res.data.temp_token)
        navigate('/auth/manager/2fa-verify')
      } else {
        toast.error('2FA required')
      }
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Login failed')
    }
  }

  return (
    <AuthLayout title="Manager Login" subtitle="Sign in to E‑Pearl Control">
      <FormProvider {...methods}>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <Input name="email" label="Email" type="email" placeholder="Enter your email" required />
          <Input name="password" label="Password" type="password" placeholder="Enter your password" required />
          <Button type="submit" disabled={isSubmitting} fullWidth>
            {isSubmitting ? 'Signing in...' : 'Sign In'}
          </Button>
        </form>
      </FormProvider>
    </AuthLayout>
  )
}

export default ManagerLogin