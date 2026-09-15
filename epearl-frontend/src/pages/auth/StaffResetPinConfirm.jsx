import React from 'react'
import { useForm, FormProvider } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import api from '../../services/api'
import AuthLayout from '../../components/auth/AuthLayout'
import Input from '../../components/common/Input'
import Button from '../../components/common/Button'
import { toast } from 'react-toastify'
import { useNavigate } from 'react-router-dom'

const schema = z.object({
  phone: z.string().min(10, 'Phone is required'),
  otp: z.string().length(6, 'OTP must be 6 digits').regex(/^\d{6}$/, 'Digits only'),
  new_pin: z.string().length(4, 'PIN must be 4 digits').regex(/^\d{4}$/, 'Digits only'),
  confirm_pin: z.string().length(4, 'Confirm PIN must be 4 digits'),
}).refine(data => data.new_pin === data.confirm_pin, {
  message: "PINs don't match",
  path: ['confirm_pin'],
})

const StaffResetPinConfirm = () => {
  const navigate = useNavigate()
  const methods = useForm({ resolver: zodResolver(schema) })
  const { handleSubmit, formState: { isSubmitting } } = methods

  const onSubmit = async (data) => {
    try {
      await api.post('/auth/staff-reset-pin-confirm/', data)
      toast.success('PIN reset successfully')
      navigate('/auth/staff/login')
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Reset failed')
    }
  }

  return (
    <AuthLayout title="Reset PIN" subtitle="Enter OTP and new PIN">
      <FormProvider {...methods}>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <Input name="phone" label="Phone" placeholder="Your phone number" required />
          <Input name="otp" label="OTP" placeholder="6-digit code" required />
          <Input name="new_pin" label="New PIN" type="password" placeholder="New 4-digit PIN" required maxLength={4} />
          <Input name="confirm_pin" label="Confirm PIN" type="password" placeholder="Confirm PIN" required maxLength={4} />
          <Button type="submit" disabled={isSubmitting} fullWidth>
            {isSubmitting ? 'Resetting...' : 'Reset PIN'}
          </Button>
        </form>
      </FormProvider>
    </AuthLayout>
  )
}

export default StaffResetPinConfirm