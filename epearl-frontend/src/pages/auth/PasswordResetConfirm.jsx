import React from 'react'
import { useForm, FormProvider } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { passwordResetConfirmSchema } from '../../utils/validators'
import api from '../../services/api'
import AuthLayout from '../../components/auth/AuthLayout'
import Input from '../../components/common/Input'
import Button from '../../components/common/Button'
import { toast } from 'react-toastify'
import { useNavigate } from 'react-router-dom'

const PasswordResetConfirm = () => {
  const navigate = useNavigate()
  const methods = useForm({ resolver: zodResolver(passwordResetConfirmSchema) })
  const { handleSubmit, formState: { isSubmitting } } = methods

  const onSubmit = async (data) => {
    try {
      await api.post('/auth/password-reset-confirm/', data)
      toast.success('Password reset successfully')
      navigate('/auth/login/customer')
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Reset failed')
    }
  }

  return (
    <AuthLayout title="Reset Password" subtitle="Enter the OTP and your new password">
      <FormProvider {...methods}>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <Input name="email" label="Email" type="email" placeholder="Your email" required />
          <Input name="otp" label="OTP" placeholder="6-digit code" required />
          <Input name="new_password" label="New Password" type="password" placeholder="New password" required />
          <Input name="confirm_password" label="Confirm Password" type="password" placeholder="Confirm new password" required />
          <Button type="submit" disabled={isSubmitting} fullWidth>
            {isSubmitting ? 'Resetting...' : 'Reset Password'}
          </Button>
        </form>
      </FormProvider>
    </AuthLayout>
  )
}

export default PasswordResetConfirm