import React, { createContext, useState, useContext, useEffect } from 'react'
import api from '../services/api'
import { toast } from 'react-toastify'

const AuthContext = createContext(null)

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)
  const [accessToken, setAccessToken] = useState(localStorage.getItem('accessToken'))
  const [refreshToken, setRefreshToken] = useState(localStorage.getItem('refreshToken'))

  useEffect(() => {
    const loadUser = async () => {
      if (!accessToken) {
        setLoading(false)
        return
      }
      try {
        api.defaults.headers.common['Authorization'] = `Bearer ${accessToken}`
        const { data } = await api.get('/auth/me/')
        setUser(data)
      } catch (err) {
        console.error('Failed to load user', err)
        logout()
      } finally {
        setLoading(false)
      }
    }
    loadUser()
  }, [accessToken])

  const login = async (email, password) => {
    try {
      const { data } = await api.post('/auth/token/', { username: email, password })
      setAccessToken(data.access)
      setRefreshToken(data.refresh)
      localStorage.setItem('accessToken', data.access)
      localStorage.setItem('refreshToken', data.refresh)
      api.defaults.headers.common['Authorization'] = `Bearer ${data.access}`
      const userRes = await api.get('/auth/me/')
      setUser(userRes.data)
      toast.success('Login successful')
      return { success: true }
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Login failed')
      return { success: false, error: err.response?.data }
    }
  }

  const logout = () => {
    setUser(null)
    setAccessToken(null)
    setRefreshToken(null)
    localStorage.removeItem('accessToken')
    localStorage.removeItem('refreshToken')
    delete api.defaults.headers.common['Authorization']
    toast.info('Logged out')
  }

  const value = {
    user,
    loading,
    accessToken,
    refreshToken,
    login,
    logout,
    setUser,
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export const useAuth = () => {
  const context = useContext(AuthContext)
  if (!context) throw new Error('useAuth must be used within AuthProvider')
  return context
}