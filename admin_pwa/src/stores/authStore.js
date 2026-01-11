import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import axios from 'axios'

const API_URL = '/api/auth'

export const useAuthStore = create(
    persist(
        (set, get) => ({
            // State
            user: null,
            accessToken: null,
            refreshToken: null,
            isAuthenticated: false,
            isLoading: false,
            error: null,

            // Actions
            login: async (username, password) => {
                set({ isLoading: true, error: null })

                try {
                    const formData = new URLSearchParams()
                    formData.append('username', username)
                    formData.append('password', password)

                    const response = await axios.post(`${API_URL}/login`, formData, {
                        headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
                    })

                    const { access_token, refresh_token } = response.data

                    // Get user info
                    const userResponse = await axios.get(`${API_URL}/me`, {
                        headers: { Authorization: `Bearer ${access_token}` }
                    })

                    set({
                        user: userResponse.data,
                        accessToken: access_token,
                        refreshToken: refresh_token,
                        isAuthenticated: true,
                        isLoading: false
                    })

                    // Set default auth header
                    axios.defaults.headers.common['Authorization'] = `Bearer ${access_token}`

                    return true
                } catch (error) {
                    set({
                        error: error.response?.data?.detail || 'Login failed',
                        isLoading: false
                    })
                    return false
                }
            },

            logout: () => {
                delete axios.defaults.headers.common['Authorization']
                set({
                    user: null,
                    accessToken: null,
                    refreshToken: null,
                    isAuthenticated: false,
                    error: null
                })
            },

            refreshAccessToken: async () => {
                const { refreshToken } = get()
                if (!refreshToken) return false

                try {
                    const response = await axios.post(`${API_URL}/refresh`, {
                        refresh_token: refreshToken
                    })

                    const { access_token, refresh_token } = response.data

                    set({
                        accessToken: access_token,
                        refreshToken: refresh_token
                    })

                    axios.defaults.headers.common['Authorization'] = `Bearer ${access_token}`

                    return true
                } catch {
                    get().logout()
                    return false
                }
            },

            initAuth: () => {
                const { accessToken } = get()
                if (accessToken) {
                    axios.defaults.headers.common['Authorization'] = `Bearer ${accessToken}`
                }
            }
        }),
        {
            name: 'autonova-auth',
            partialize: (state) => ({
                user: state.user,
                accessToken: state.accessToken,
                refreshToken: state.refreshToken,
                isAuthenticated: state.isAuthenticated
            })
        }
    )
)

// Initialize auth on load
useAuthStore.getState().initAuth()
