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
  old_pin: z.string().length(4, 'Old PIN must be 4 digits').regex(/^\d{4}$/, 'Digits only'),
  new_pin: z.string().length(4, 'New PIN must be 4 digits').regex(/^\d{4}$/, 'Digits only'),
  confirm_pin: z.string().length(4, 'Confirm PIN must be 4 digits'),
}).refine(data => data.new_pin === data.confirm_pin, {
  message: "PINs don't match",
  path: ['confirm_pin'],
})

const StaffChangePin = () => {
  const navigate = useNavigate()
  const methods = useForm({ resolver: zodResolver(schema) })
  const { handleSubmit, formState: { isSubmitting } } = methods

  const onSubmit = async (data) => {
    try {
      await api.post('/auth/staff-change-pin/', data)
      toast.success('PIN changed successfully')
      navigate('/')
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to change PIN')
    }
  }

  return (
    <AuthLayout title="Change PIN" subtitle="Update your staff PIN">
      <FormProvider {...methods}>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <Input name="old_pin" label="Current PIN" type="password" placeholder="Current PIN" required maxLength={4} />
          <Input name="new_pin" label="New PIN" type="password" placeholder="New PIN" required maxLength={4} />
          <Input name="confirm_pin" label="Confirm PIN" type="password" placeholder="Confirm new PIN" required maxLength={4} />
          <Button type="submit" disabled={isSubmitting} fullWidth>
            {isSubmitting ? 'Changing...' : 'Change PIN'}
          </Button>
        </form>
      </FormProvider>
    </AuthLayout>
  )
}

export default StaffChangePin