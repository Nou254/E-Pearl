import React from 'react'
import { useForm, FormProvider } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import api from '../../services/api'
import AuthLayout from '../../components/auth/AuthLayout'
import Input from '../../components/common/Input'
import Button from '../../components/common/Button'
import { toast } from 'react-toastify'

const schema = z.object({ phone: z.string().min(10, 'Phone is required') })

const StaffResetPinRequest = () => {
  const methods = useForm({ resolver: zodResolver(schema) })
  const { handleSubmit, formState: { isSubmitting } } = methods

  const onSubmit = async (data) => {
    try {
      await api.post('/auth/staff-reset-pin-request/', data)
      toast.success('OTP sent to your phone')
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to send OTP')
    }
  }

  return (
    <AuthLayout title="Reset PIN" subtitle="Enter your phone to receive an OTP">
      <FormProvider {...methods}>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <Input name="phone" label="Phone" placeholder="Your phone number" required />
          <Button type="submit" disabled={isSubmitting} fullWidth>
            {isSubmitting ? 'Sending...' : 'Send OTP'}
          </Button>
        </form>
      </FormProvider>
    </AuthLayout>
  )
}

export default StaffResetPinRequest