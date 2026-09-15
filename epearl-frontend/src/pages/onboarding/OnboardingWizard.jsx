import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import Step1Documents from './steps/Step1Documents'
import Step2Profile from './steps/Step2Profile'
import Step3FloorPlan from './steps/Step3FloorPlan'
import Step4Menu from './steps/Step4Menu'
import Step5QR from './steps/Step5QR'
import Step6Payment from './steps/Step6Payment'
import { useAuth } from '../../context/AuthContext'
import api from '../../services/api'
import { toast } from 'react-toastify'
import LoadingSpinner from '../../components/common/LoadingSpinner'

const STEPS = [
  { id: 'documents', label: 'Documents', component: Step1Documents },
  { id: 'profile', label: 'Profile', component: Step2Profile },
  { id: 'floorplan', label: 'Floor Plan', component: Step3FloorPlan },
  { id: 'menu', label: 'Menu', component: Step4Menu },
  { id: 'qr', label: 'QR Codes', component: Step5QR },
  { id: 'payment', label: 'Payment', component: Step6Payment },
]

const OnboardingWizard = () => {
  const { user } = useAuth()
  const navigate = useNavigate()
  const [currentStep, setCurrentStep] = useState(0)
  const [loading, setLoading] = useState(false)
  const [formData, setFormData] = useState({})
  const [venueId, setVenueId] = useState(user?.venue?.id || null)

  const nextStep = (data) => {
    setFormData(prev => ({ ...prev, ...data }))
    if (currentStep === STEPS.length - 1) {
      finishOnboarding(data)
    } else {
      setCurrentStep(prev => prev + 1)
    }
  }

  const prevStep = () => {
    setCurrentStep(prev => Math.max(0, prev - 1))
  }

  const finishOnboarding = async (data) => {
    setLoading(true)
    try {
      // Final step: mark onboarding complete
      await api.post(`/control/update-onboarding-step/`, {
        step: 'complete',
        completed_at: new Date().toISOString(),
      })
      toast.success('Onboarding complete! Welcome to E‑Pearl.')
      navigate('/control')
    } catch (err) {
      toast.error('Failed to complete onboarding')
    } finally {
      setLoading(false)
    }
  }

  const StepComponent = STEPS[currentStep].component

  return (
    <div className="min-h-screen bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-3xl mx-auto">
        <div className="mb-8">
          <h1 className="text-2xl font-bold text-gray-900">Venue Onboarding</h1>
          <p className="text-sm text-gray-500">Step {currentStep + 1} of {STEPS.length}: {STEPS[currentStep].label}</p>
          <div className="mt-2 h-2 bg-gray-200 rounded-full overflow-hidden">
            <div className="h-full bg-primary-600 rounded-full transition-all duration-300" style={{ width: `${((currentStep + 1) / STEPS.length) * 100}%` }} />
          </div>
        </div>

        {loading ? (
          <div className="flex justify-center py-12">
            <LoadingSpinner />
          </div>
        ) : (
          <StepComponent
            venueId={venueId}
            nextStep={nextStep}
            prevStep={prevStep}
            formData={formData}
            isFirst={currentStep === 0}
            isLast={currentStep === STEPS.length - 1}
          />
        )}
      </div>
    </div>
  )
}

export default OnboardingWizard