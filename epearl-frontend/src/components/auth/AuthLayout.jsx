import React from 'react'
import { Link } from 'react-router-dom'
import Card from '../common/Card'

const AuthLayout = ({ children, title, subtitle, footer, maxWidth = 'sm' }) => {
  const maxWidthClasses = {
    sm: 'max-w-md',
    md: 'max-w-lg',
    lg: 'max-w-2xl',
  }

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col justify-center py-12 sm:px-6 lg:px-8">
      <div className={`mx-auto w-full ${maxWidthClasses[maxWidth]}`}>
        <div className="text-center mb-6">
          <Link to="/" className="inline-block">
            <h1 className="text-3xl font-extrabold text-primary-600">E‑Pearl</h1>
          </Link>
        </div>
        <Card title={title} subtitle={subtitle}>
          {children}
        </Card>
        {footer && <div className="mt-4 text-center text-sm text-gray-600">{footer}</div>}
      </div>
    </div>
  )
}

export default AuthLayout