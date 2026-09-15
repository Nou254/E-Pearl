import React from 'react'
import { useFormContext } from 'react-hook-form'

const Input = ({ name, label, type = 'text', placeholder, required, disabled, className = '' }) => {
  const { register, formState: { errors } } = useFormContext()
  const error = errors[name]

  return (
    <div className="w-full">
      {label && (
        <label htmlFor={name} className="block text-sm font-medium text-gray-700 mb-1">
          {label} {required && <span className="text-red-500">*</span>}
        </label>
      )}
      <input
        id={name}
        type={type}
        placeholder={placeholder}
        disabled={disabled}
        className={`w-full px-4 py-2.5 border rounded-lg transition-colors duration-200
          ${error ? 'border-red-500 ring-1 ring-red-500' : 'border-gray-300 focus:border-primary-500 focus:ring-1 focus:ring-primary-500'}
          ${disabled ? 'bg-gray-100 cursor-not-allowed' : 'bg-white'}
          ${className}`}
        {...register(name)}
      />
      {error && <p className="mt-1 text-sm text-red-600">{error.message}</p>}
    </div>
  )
}

export default Input