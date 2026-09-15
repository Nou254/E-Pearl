import { z } from 'zod'

export const emailSchema = z.string().email('Invalid email address')
export const phoneSchema = z.string().min(10, 'Phone number must be at least 10 digits')
export const passwordSchema = z.string().min(8, 'Password must be at least 8 characters')
  .regex(/[A-Z]/, 'Must contain at least one uppercase letter')
  .regex(/[a-z]/, 'Must contain at least one lowercase letter')
  .regex(/[0-9]/, 'Must contain at least one number')
  .regex(/[^A-Za-z0-9]/, 'Must contain at least one special character')

export const customerSignupSchema = z.object({
  full_name: z.string().min(2, 'Name is required'),
  email: emailSchema,
  phone: phoneSchema,
  password: passwordSchema,
  confirm_password: z.string(),
}).refine(data => data.password === data.confirm_password, {
  message: "Passwords don't match",
  path: ['confirm_password'],
})

export const customerLoginSchema = z.object({
  username: z.string().min(1, 'Email or phone is required'),
  password: z.string().min(1, 'Password is required'),
})

export const staffLoginSchema = z.object({
  phone: phoneSchema,
  pin: z.string().length(4, 'PIN must be 4 digits').regex(/^\d{4}$/, 'PIN must be digits'),
})

export const staffSetPinSchema = z.object({
  phone: phoneSchema,
  otp: z.string().length(6, 'OTP must be 6 digits').regex(/^\d{6}$/, 'OTP must be digits'),
  pin: z.string().length(4, 'PIN must be 4 digits').regex(/^\d{4}$/, 'PIN must be digits'),
  confirm_pin: z.string().length(4, 'Confirm PIN must be 4 digits'),
}).refine(data => data.pin === data.confirm_pin, {
  message: "PINs don't match",
  path: ['confirm_pin'],
})

export const managerLoginSchema = z.object({
  email: emailSchema,
  password: z.string().min(1, 'Password is required'),
})

export const otpVerifySchema = z.object({
  otp: z.string().length(6, 'OTP must be 6 digits').regex(/^\d{6}$/, 'OTP must be digits'),
})

export const passwordResetRequestSchema = z.object({
  email: emailSchema.optional(),
  phone: phoneSchema.optional(),
}).refine(data => data.email || data.phone, {
  message: 'Email or phone is required',
  path: ['email'],
})

export const passwordResetConfirmSchema = z.object({
  email: emailSchema,
  otp: z.string().length(6, 'OTP must be 6 digits').regex(/^\d{6}$/, 'OTP must be digits'),
  new_password: passwordSchema,
  confirm_password: z.string(),
}).refine(data => data.new_password === data.confirm_password, {
  message: "Passwords don't match",
  path: ['confirm_password'],
})