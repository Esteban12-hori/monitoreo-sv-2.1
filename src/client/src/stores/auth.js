import { defineStore } from 'pinia'
import axios from 'axios'

const API_BASE = '/api'

export const useAuthStore = defineStore('auth', {
  state: () => ({
    token: localStorage.getItem('token') || null,
    user: JSON.parse(localStorage.getItem('user')) || null,
  }),
  getters: {
    isAuthenticated: (state) => !!state.token,
    isAdmin: (state) => state.user?.is_admin || false,
    isBlocked: (state) => state.user?.is_blocked || false,
    mustChangePassword: (state) => state.user?.must_change_password || false,
  },
  actions: {
    async login(email, password) {
      try {
        const response = await axios.post(`${API_BASE}/login`, {
          email,
          password
        })
        
        const data = response.data
        this.token = data.token
        this.user = {
          email: data.email,
          name: data.name,
          is_admin: data.is_admin,
          must_change_password: data.must_change_password,
          is_blocked: data.is_blocked
        }
        
        localStorage.setItem('token', this.token)
        localStorage.setItem('user', JSON.stringify(this.user))
        
        return true
      } catch (error) {
        console.error("Login failed", error)
        throw error
      }
    },
    updateUserLocal(patch) {
      if (!this.user) return
      this.user = { ...this.user, ...patch }
      localStorage.setItem('user', JSON.stringify(this.user))
    },
    logout() {
      // Optional: Call backend logout
      if (this.token) {
          axios.post(`${API_BASE}/logout`, {}, {
              headers: { 'X-Dashboard-Token': this.token }
          }).catch(err => console.warn(err))
      }
      
      this.token = null
      this.user = null
      localStorage.removeItem('token')
      localStorage.removeItem('user')
    },
    // Helper to get headers for other requests
    getHeaders() {
      return {
        'Content-Type': 'application/json',
        'X-Dashboard-Token': this.token
      }
    }
  }
})
