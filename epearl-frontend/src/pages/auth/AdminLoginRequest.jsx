import React from 'react'
import { useForm, FormProvider } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import api from '../../services/api'
import AuthLayout from '../../components/auth/AuthLayout'
import Input from '../../components/common/Input'
import Button from '../../components/common/Button'
import { toast } from 'react-toastify'

const schema = z.object({ email: z.string().email('Invalid email') })

const AdminLoginRequest = () => {
  const methods = useForm({ resolver: zodResolver(schema) })
  const { handleSubmit, formState: { isSubmitting } } = methods

  const onSubmit = async (data) => {
    try {
      await api.post('/auth/admin-login-request/', data)
      toast.success('Login link sent to your email')
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Request failed')
    }
  }

  return (
    <AuthLayout title="Admin Login" subtitle="Enter your email to receive a magic link">
      <FormProvider {...methods}>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <Input name="email" label="Email" type="email" placeholder="Your admin email" required />
          <Button type="submit" disabled={isSubmitting} fullWidth>
            {isSubmitting ? 'Sending...' : 'Send Magic Link'}
          </Button>
        </form>
      </FormProvider>
    </AuthLayout>
  )
}

export default AdminLoginRequest