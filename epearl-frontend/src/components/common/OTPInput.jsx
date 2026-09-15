import React, { useRef, useState, useEffect } from 'react'

const OTPInput = ({ length = 6, onComplete, disabled = false }) => {
  const [otp, setOtp] = useState(Array(length).fill(''))
  const inputs = useRef([])

  useEffect(() => {
    if (otp.every(v => v !== '')) {
      onComplete?.(otp.join(''))
    }
  }, [otp, onComplete])

  const handleChange = (index, value) => {
    if (!/^\d*$/.test(value)) return
    const newOtp = [...otp]
    newOtp[index] = value.slice(-1)
    setOtp(newOtp)
    if (value && index < length - 1) {
      inputs.current[index + 1].focus()
    }
  }

  const handleKeyDown = (index, e) => {
    if (e.key === 'Backspace' && !otp[index] && index > 0) {
      inputs.current[index - 1].focus()
    }
  }

  return (
    <div className="flex gap-2 justify-center">
      {otp.map((digit, idx) => (
        <input
          key={idx}
          ref={el => inputs.current[idx] = el}
          type="text"
          inputMode="numeric"
          maxLength={1}
          value={digit}
          onChange={e => handleChange(idx, e.target.value)}
          onKeyDown={e => handleKeyDown(idx, e)}
          disabled={disabled}
          className="w-12 h-14 text-center text-2xl font-semibold border-2 border-gray-300 rounded-lg focus:border-primary-500 focus:ring-1 focus:ring-primary-500 disabled:bg-gray-100"
        />
      ))}
    </div>
  )
}

export default OTPInput