import React, { useState } from 'react'
import { useForm, FormProvider } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import Input from '../../../components/common/Input'
import Button from '../../../components/common/Button'
import api from '../../../services/api'
import { toast } from 'react-toastify'

const schema = z.object({
  kra_pin: z.string().min(5, 'KRA PIN is required'),
  registration_number: z.string().min(3, 'Registration number is required'),
})

const Step1Documents = ({ venueId, nextStep, formData }) => {
  const [file, setFile] = useState(null)
  const [uploading, setUploading] = useState(false)
  const methods = useForm({
    resolver: zodResolver(schema),
    defaultValues: formData,
  })
  const { handleSubmit, formState: { isSubmitting } } = methods

  const onSubmit = async (data) => {
    if (!venueId) {
      // Register venue first
      try {
        const res = await api.post('/venues/register/', data)
        const newVenueId = res.data.id
        // Upload document if file selected
        if (file) {
          const formData2 = new FormData()
          formData2.append('document_type', 'kra_pin')
          formData2.append('file', file)
          await api.post(`/venues/${newVenueId}/upload-document/`, formData2, {
            headers: { 'Content-Type': 'multipart/form-data' }
          })
        }
        toast.success('Venue registered!')
        nextStep({ venue_id: newVenueId, ...data })
      } catch (err) {
        toast.error(err.response?.data?.detail || 'Registration failed')
      }
    } else {
      nextStep(data)
    }
  }

  const handleFileChange = (e) => {
    setFile(e.target.files[0])
  }

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <FormProvider {...methods}>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <Input name="business_name" label="Business Name" placeholder="Enter business name" required />
          <Input name="registration_number" label="Registration Number" placeholder="e.g., 123456" required />
          <Input name="kra_pin" label="KRA PIN" placeholder="e.g., A123456789" required />
          <div>
            <label className="block text-sm font-medium text-gray-700">Upload KRA PIN Certificate</label>
            <input type="file" accept="image/*,.pdf" onChange={handleFileChange} className="mt-1 block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-semibold file:bg-primary-50 file:text-primary-700 hover:file:bg-primary-100" />
          </div>
          <div className="flex justify-end">
            <Button type="submit" disabled={isSubmitting}>
              {isSubmitting ? 'Saving...' : 'Next'}
            </Button>
          </div>
        </form>
      </FormProvider>
    </div>
  )
}

export default Step1Documents