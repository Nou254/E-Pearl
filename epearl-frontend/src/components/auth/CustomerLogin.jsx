import React from 'react'
import { useForm, FormProvider } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { Link, useNavigate } from 'react-router-dom'
import { customerLoginSchema } from '../../utils/validators'
import AuthLayout from '../../components/auth/AuthLayout'
import Input from '../../components/common/Input'
import Button from '../../components/common/Button'
import { useAuth } from '../../context/AuthContext'

const CustomerLogin = () => {
  const { login } = useAuth()
  const navigate = useNavigate()
  const methods = useForm({ resolver: zodResolver(customerLoginSchema) })
  const { handleSubmit, formState: { isSubmitting } } = methods

  const onSubmit = async (data) => {
    const result = await login(data.username, data.password)
    if (result.success) {
      navigate('/')
    }
  }

  return (
    <AuthLayout title="Welcome Back" subtitle="Sign in to your customer account">
      <FormProvider {...methods}>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <Input name="username" label="Email or Phone" placeholder="Enter your email or phone" required />
          <Input name="password" label="Password" type="password" placeholder="Enter your password" required />
          <div className="flex items-center justify-between text-sm">
            <Link to="/auth/password-reset" className="text-primary-600 hover:underline">Forgot password?</Link>
            <Link to="/auth/signup" className="text-primary-600 hover:underline">Create account</Link>
          </div>
          <Button type="submit" disabled={isSubmitting} fullWidth>
            {isSubmitting ? 'Signing in...' : 'Sign In'}
          </Button>
        </form>
      </FormProvider>
    </AuthLayout>
  )
}

export default CustomerLogin