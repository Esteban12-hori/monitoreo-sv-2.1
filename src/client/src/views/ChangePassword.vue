<script setup>
import { ref, computed } from 'vue'
import { useAuthStore } from '../stores/auth'
import { useRouter } from 'vue-router'
import axios from 'axios'

const authStore = useAuthStore()
const router = useRouter()

const currentPassword = ref('')
const newPassword = ref('')
const confirmPassword = ref('')
const error = ref('')
const success = ref('')
const loading = ref(false)

const isValid = computed(() => {
  const p = newPassword.value
  return p.length >= 12 && /[A-Z]/.test(p) && /[0-9]/.test(p)
})

const submit = async () => {
  if (newPassword.value !== confirmPassword.value) {
    error.value = "Passwords do not match"
    return
  }
  if (!isValid.value) {
    error.value = "Password does not meet requirements"
    return
  }

  loading.value = true
  error.value = ''
  
  try {
    await axios.post('/api/users/change-password', {
      current_password: currentPassword.value,
      new_password: newPassword.value
    }, {
      headers: authStore.getHeaders()
    })
    
    // Update local user state
    authStore.user.must_change_password = false
    localStorage.setItem('user', JSON.stringify(authStore.user))
    
    success.value = "Password changed successfully! Redirecting..."
    
    setTimeout(() => {
        router.push('/')
    }, 1500)
    
  } catch (e) {
    error.value = e.response?.data?.detail || "Error changing password"
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="min-h-screen flex items-center justify-center bg-gray-100 dark:bg-gray-900 transition-colors duration-200">
    <div class="bg-white dark:bg-gray-800 p-8 rounded-2xl shadow-2xl w-full max-w-md border border-gray-100 dark:border-gray-700">
      <div class="text-center mb-8">
        <div class="inline-flex items-center justify-center h-14 w-14 rounded-2xl bg-red-50 dark:bg-red-900/30 mb-4 text-red-600 dark:text-red-400">
            <svg class="h-7 w-7" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
            </svg>
        </div>
        <h2 class="text-2xl font-bold text-gray-900 dark:text-white">Security Update Required</h2>
        <p class="text-sm text-gray-500 dark:text-gray-400 mt-2">You must change your password to continue.</p>
      </div>

      <div v-if="error" class="bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-800 text-red-700 dark:text-red-300 px-4 py-3 rounded-md mb-6 text-sm">
        {{ error }}
      </div>
      <div v-if="success" class="bg-green-50 dark:bg-green-900/30 border border-green-200 dark:border-green-800 text-green-700 dark:text-green-300 px-4 py-3 rounded-md mb-6 text-sm">
        {{ success }}
      </div>

      <form @submit.prevent="submit" v-if="!success">
        <div class="space-y-4">
            <div>
                <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Current Password</label>
                <input v-model="currentPassword" type="password" class="block w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 sm:text-sm" required>
            </div>
            <div>
                <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">New Password</label>
                <input v-model="newPassword" type="password" class="block w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 sm:text-sm" required>
                <ul class="text-xs mt-2 text-gray-500 dark:text-gray-400 list-disc pl-4 space-y-1">
                    <li :class="{'text-green-600 dark:text-green-400': newPassword.length >= 12}">Min 12 characters</li>
                    <li :class="{'text-green-600 dark:text-green-400': /[A-Z]/.test(newPassword)}">At least one uppercase</li>
                    <li :class="{'text-green-600 dark:text-green-400': /[0-9]/.test(newPassword)}">At least one number</li>
                </ul>
            </div>
            <div>
                <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Confirm New Password</label>
                <input v-model="confirmPassword" type="password" class="block w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 sm:text-sm" required>
            </div>
        </div>
        
        <div class="mt-6">
            <button type="submit" :disabled="!isValid || loading" class="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors">
                {{ loading ? 'Updating...' : 'Change Password' }}
            </button>
        </div>
      </form>
      
      <div class="mt-4 text-center">
        <button @click="authStore.logout(); router.push('/login')" class="text-sm text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300">
            Log out
        </button>
      </div>
    </div>
  </div>
</template>
