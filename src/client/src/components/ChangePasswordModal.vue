<script setup>
import { ref, computed } from 'vue'
import { useAuthStore } from '../stores/auth'
import axios from 'axios'

const authStore = useAuthStore()
const currentPassword = ref('')
const newPassword = ref('')
const confirmPassword = ref('')
const error = ref('')
const success = ref('')
const showCurrent = ref(false)
const showNew = ref(false)
const showConfirm = ref(false)

const isValid = computed(() => {
  const p = newPassword.value
  return p.length >= 12 && /[A-Z]/.test(p) && /[0-9]/.test(p)
})

const submit = async () => {
  if (newPassword.value !== confirmPassword.value) {
    error.value = "Las contraseñas no coinciden"
    return
  }
  if (!isValid.value) {
    error.value = "La contraseña no cumple con los requisitos"
    return
  }

  try {
    await axios.post('/api/users/change-password', {
      current_password: currentPassword.value,
      new_password: newPassword.value
    }, {
      headers: authStore.getHeaders()
    })
    
    authStore.updateUserLocal({ must_change_password: false })
    success.value = "¡Contraseña actualizada exitosamente!"
    // Close modal handled by parent or state
  } catch (e) {
    error.value = e.response?.data?.detail || "Error al cambiar la contraseña"
  }
}
</script>

<template>
  <div v-if="authStore.mustChangePassword" class="fixed inset-0 z-50 overflow-y-auto" aria-labelledby="modal-title" role="dialog" aria-modal="true">
    <!-- Backdrop with blur -->
    <div class="fixed inset-0 bg-gray-900/50 dark:bg-black/70 backdrop-blur-sm transition-opacity"></div>

    <div class="flex min-h-full items-end justify-center p-4 text-center sm:items-center sm:p-0">
      <!-- Modal panel -->
      <div class="relative transform overflow-hidden rounded-2xl bg-white dark:bg-gray-800 text-left shadow-2xl ring-1 ring-black/5 transition-all sm:my-8 sm:w-full sm:max-w-md border border-gray-100 dark:border-gray-700">
        <div class="px-4 pb-4 pt-5 sm:p-6 sm:pb-4">
          <div class="sm:flex sm:items-start">
            <div class="mx-auto flex h-12 w-12 flex-shrink-0 items-center justify-center rounded-full bg-red-100 dark:bg-red-900/30 sm:mx-0 sm:h-10 sm:w-10">
              <svg class="h-6 w-6 text-red-600 dark:text-red-400" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" aria-hidden="true">
                <path stroke-linecap="round" stroke-linejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" />
              </svg>
            </div>
            <div class="mt-3 text-center sm:ml-4 sm:mt-0 sm:text-left w-full">
              <h3 class="text-base font-semibold leading-6 text-gray-900 dark:text-white" id="modal-title">Actualización de Seguridad Requerida</h3>
              <div class="mt-2">
                <p class="text-sm text-gray-500 dark:text-gray-400">Por motivos de seguridad, debes cambiar tu contraseña predeterminada para continuar.</p>
              </div>
              
              <div v-if="error" class="mt-4 p-3 rounded-lg bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-300 text-sm border border-red-100 dark:border-red-800 flex items-center gap-2">
                <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                {{ error }}
              </div>
              
              <div v-if="success" class="mt-4 p-3 rounded-lg bg-green-50 dark:bg-green-900/20 text-green-700 dark:text-green-300 text-sm border border-green-100 dark:border-green-800 flex items-center gap-2">
                <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
                </svg>
                {{ success }}
              </div>

              <form @submit.prevent="submit" v-if="!success" class="mt-6 space-y-4">
                <div>
                  <label class="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">Contraseña Actual</label>
                  <div class="relative">
                    <input 
                      v-model="currentPassword" 
                      :type="showCurrent ? 'text' : 'password'" 
                      class="block w-full rounded-lg border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm py-2 pr-10" 
                      required
                    >
                    <button
                      type="button"
                      class="absolute inset-y-0 right-0 px-3 flex items-center text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 focus:outline-none"
                      @click="showCurrent = !showCurrent"
                    >
                      <svg v-if="!showCurrent" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.477 0 8.268 2.943 9.542 7-1.274 4.057-5.065 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                      </svg>
                      <svg v-else class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13.875 18.825A10.05 10.05 0 0112 19c-4.477 0-8.268-2.943-9.542-7a9.956 9.956 0 012.242-3.772M6.228 6.228A9.956 9.956 0 0112 5c4.477 0 8.268 2.943 9.542 7a9.965 9.965 0 01-4.043 5.197M15 12a3 3 0 00-3-3m0 0a3 3 0 00-2.121.879M12 9l-2-2m0 0L4 4m6 3l2-2m0 0l6-3m-6 3l3 3" />
                      </svg>
                    </button>
                  </div>
                </div>
                
                <div>
                  <label class="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">Nueva Contraseña</label>
                  <div class="relative">
                    <input 
                      v-model="newPassword" 
                      :type="showNew ? 'text' : 'password'" 
                      class="block w-full rounded-lg border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm py-2 pr-10" 
                      required
                    >
                    <button
                      type="button"
                      class="absolute inset-y-0 right-0 px-3 flex items-center text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 focus:outline-none"
                      @click="showNew = !showNew"
                    >
                      <svg v-if="!showNew" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.477 0 8.268 2.943 9.542 7-1.274 4.057-5.065 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                      </svg>
                      <svg v-else class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13.875 18.825A10.05 10.05 0 0112 19c-4.477 0-8.268-2.943-9.542-7a9.956 9.956 0 012.242-3.772M6.228 6.228A9.956 9.956 0 0112 5c4.477 0 8.268 2.943 9.542 7a9.965 9.965 0 01-4.043 5.197M15 12a3 3 0 00-3-3m0 0a3 3 0 00-2.121.879M12 9l-2-2m0 0L4 4m6 3l2-2m0 0l6-3m-6 3l3 3" />
                      </svg>
                    </button>
                  </div>
                  <ul class="text-xs mt-2 space-y-1 text-gray-500 dark:text-gray-400">
                    <li class="flex items-center gap-1.5" :class="{'text-emerald-600 dark:text-emerald-400': newPassword.length >= 12}">
                      <svg class="w-3 h-3" :class="newPassword.length >= 12 ? 'opacity-100' : 'opacity-0'" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="3" d="M5 13l4 4L19 7" /></svg>
                      Mínimo 12 caracteres
                    </li>
                    <li class="flex items-center gap-1.5" :class="{'text-emerald-600 dark:text-emerald-400': /[A-Z]/.test(newPassword)}">
                      <svg class="w-3 h-3" :class="/[A-Z]/.test(newPassword) ? 'opacity-100' : 'opacity-0'" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="3" d="M5 13l4 4L19 7" /></svg>
                      Al menos una mayúscula
                    </li>
                    <li class="flex items-center gap-1.5" :class="{'text-emerald-600 dark:text-emerald-400': /[0-9]/.test(newPassword)}">
                      <svg class="w-3 h-3" :class="/[0-9]/.test(newPassword) ? 'opacity-100' : 'opacity-0'" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="3" d="M5 13l4 4L19 7" /></svg>
                      Al menos un número
                    </li>
                  </ul>
                </div>

                <div>
                  <label class="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">Confirmar Nueva Contraseña</label>
                  <div class="relative">
                    <input 
                      v-model="confirmPassword" 
                      :type="showConfirm ? 'text' : 'password'" 
                      class="block w-full rounded-lg border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm py-2 pr-10" 
                      required
                      @input="error = ''"
                    >
                    <button
                      type="button"
                      class="absolute inset-y-0 right-0 px-3 flex items-center text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 focus:outline-none"
                      @click="showConfirm = !showConfirm"
                    >
                      <svg v-if="!showConfirm" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.477 0 8.268 2.943 9.542 7-1.274 4.057-5.065 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                      </svg>
                      <svg v-else class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13.875 18.825A10.05 10.05 0 0112 19c-4.477 0-8.268-2.943-9.542-7a9.956 9.956 0 012.242-3.772M6.228 6.228A9.956 9.956 0 0112 5c4.477 0 8.268 2.943 9.542 7a9.965 9.965 0 01-4.043 5.197M15 12a3 3 0 00-3-3m0 0a3 3 0 00-2.121.879M12 9l-2-2m0 0L4 4m6 3l2-2m0 0l6-3m-6 3l3 3" />
                      </svg>
                    </button>
                  </div>
                </div>

                <div class="pt-2">
                  <button 
                    type="submit" 
                    class="w-full flex w-full justify-center rounded-lg bg-indigo-600 px-3 py-2 text-sm font-semibold text-white shadow-sm hover:bg-indigo-500 sm:ml-3 sm:w-auto transition-all"
                  >
                    Actualizar Contraseña
                  </button>
                </div>
              </form>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
