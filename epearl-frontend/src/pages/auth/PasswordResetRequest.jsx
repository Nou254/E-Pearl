import React from 'react'
import { useForm, FormProvider } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { passwordResetRequestSchema } from '../../utils/validators'
import api from '../../services/api'
import AuthLayout from '../../components/auth/AuthLayout'
import Input from '../../components/common/Input'
import Button from '../../components/common/Button'
import { toast } from 'react-toastify'

const PasswordResetRequest = () => {
  const methods = useForm({ resolver: zodResolver(passwordResetRequestSchema) })
  const { handleSubmit, formState: { isSubmitting } } = methods

  const onSubmit = async (data) => {
    try {
      await api.post('/auth/password-reset-request/', data)
      toast.success('OTP sent to your email/phone')
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to send OTP')
    }
  }

  return (
    <AuthLayout title="Reset Password" subtitle="Enter your email or phone to receive an OTP">
      <FormProvider {...methods}>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <Input name="email" label="Email" type="email" placeholder="Your email address" />
          <Input name="phone" label="Phone" placeholder="Your phone number" />
          <Button type="submit" disabled={isSubmitting} fullWidth>
            {isSubmitting ? 'Sending...' : 'Send OTP'}
          </Button>
        </form>
      </FormProvider>
    </AuthLayout>
  )
}

export default PasswordResetRequest