import React from 'react'
import { useForm, FormProvider } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { useNavigate } from 'react-router-dom'
import { customerSignupSchema } from '../../utils/validators'
import api from '../../services/api'
import AuthLayout from '../../components/auth/AuthLayout'
import Input from '../../components/common/Input'
import Button from '../../components/common/Button'
import { toast } from 'react-toastify'

const CustomerSignup = () => {
  const navigate = useNavigate()
  const methods = useForm({ resolver: zodResolver(customerSignupSchema) })
  const { handleSubmit, formState: { isSubmitting } } = methods

  const onSubmit = async (data) => {
    try {
      await api.post('/auth/register-customer/', data)
      toast.success('Account created! Please login.')
      navigate('/auth/login/customer')
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Registration failed')
    }
  }

  return (
    <AuthLayout title="Create Account" subtitle="Join the E‑Pearl community">
      <FormProvider {...methods}>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <Input name="full_name" label="Full Name" placeholder="Enter your full name" required />
          <Input name="email" label="Email" type="email" placeholder="Enter your email" required />
          <Input name="phone" label="Phone Number" placeholder="e.g., 254700000000" required />
          <Input name="password" label="Password" type="password" placeholder="Create a strong password" required />
          <Input name="confirm_password" label="Confirm Password" type="password" placeholder="Confirm your password" required />
          <Button type="submit" disabled={isSubmitting} fullWidth>
            {isSubmitting ? 'Creating account...' : 'Sign Up'}
          </Button>
          <p className="text-sm text-center text-gray-600">
            Already have an account? <Link to="/auth/login/customer" className="text-primary-600 hover:underline">Sign In</Link>
          </p>
        </form>
      </FormProvider>
    </AuthLayout>
  )
}

export default CustomerSignup