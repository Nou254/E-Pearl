import React from 'react'
import { useForm, FormProvider } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { staffSetPinSchema } from '../../utils/validators'
import api from '../../services/api'
import AuthLayout from '../../components/auth/AuthLayout'
import Input from '../../components/common/Input'
import Button from '../../components/common/Button'
import { toast } from 'react-toastify'
import { useNavigate } from 'react-router-dom'

const StaffSetPin = () => {
  const navigate = useNavigate()
  const methods = useForm({ resolver: zodResolver(staffSetPinSchema) })
  const { handleSubmit, formState: { isSubmitting } } = methods

  const onSubmit = async (data) => {
    try {
      await api.post('/auth/staff-set-pin/', data)
      toast.success('PIN set successfully')
      navigate('/auth/staff/login')
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to set PIN')
    }
  }

  return (
    <AuthLayout title="Set PIN" subtitle="Create your 4-digit PIN for staff access">
      <FormProvider {...methods}>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <Input name="phone" label="Phone" placeholder="Your phone number" required />
          <Input name="otp" label="OTP" placeholder="6-digit OTP" required />
          <Input name="pin" label="New PIN" type="password" placeholder="4-digit PIN" required maxLength={4} />
          <Input name="confirm_pin" label="Confirm PIN" type="password" placeholder="Confirm PIN" required maxLength={4} />
          <Button type="submit" disabled={isSubmitting} fullWidth>
            {isSubmitting ? 'Setting PIN...' : 'Set PIN'}
          </Button>
        </form>
      </FormProvider>
    </AuthLayout>
  )
}

export default StaffSetPin