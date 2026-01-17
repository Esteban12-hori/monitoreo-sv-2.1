<script setup>
import { ref, onMounted } from 'vue'
import axios from 'axios'
import { useAuthStore } from '../stores/auth'
import { useRouter } from 'vue-router'

const authStore = useAuthStore()
const router = useRouter()

const config = ref({
  host: '',
  port: 587,
  username: '',
  password: '',
  use_ssl: false,
  use_tls: true,
  sender_email: ''
})

const loading = ref(false)
const message = ref('')
const error = ref('')
const smtpNotConfigured = ref(false)
const servers = ref([])
const savingGroup = ref(null)
const savingInterval = ref(null)

const intervalOptions = [
  { value: 0, label: 'Desactivado' },
  { value: 5, label: 'Tiempo real (5s)' },
  { value: 300, label: '5 minutos' },
  { value: 600, label: '10 minutos' },
  { value: 1800, label: '30 minutos' },
  { value: 3600, label: '60 minutos' },
  { value: 5 * 3600, label: '5 horas' },
  { value: 7 * 3600, label: '7 horas' },
  { value: 8 * 3600, label: '8 horas' },
  { value: 10 * 3600, label: '10 horas' },
  { value: 24 * 3600, label: '24 horas' }
]

onMounted(async () => {
  try {
    const res = await axios.get('/api/admin/smtp/config', {
      headers: authStore.getHeaders()
    })
    if (res.data) {
        config.value = { ...config.value, ...res.data, password: '' } // Don't show password
    }
  } catch (e) {
    if (e.response && e.response.status === 404) {
      smtpNotConfigured.value = true
    }
  }

  try {
    const srvRes = await axios.get('/api/servers', {
      headers: authStore.getHeaders()
    })
    servers.value = srvRes.data.map(s => ({
      ...s,
      editGroup: s.group_name || '',
      editInterval: s.report_interval ?? 2400
    }))
  } catch (e) {
    console.error('Error cargando servidores', e)
  }
})

const testConnection = async () => {
  loading.value = true
  message.value = ''
  error.value = ''
  try {
    await axios.post('/api/admin/smtp/test', config.value, {
      headers: authStore.getHeaders()
    })
    message.value = "Connection successful!"
  } catch (e) {
    error.value = "Connection failed: " + (e.response?.data?.detail || e.message)
  } finally {
    loading.value = false
  }
}

const saveConfig = async () => {
  loading.value = true
  message.value = ''
  error.value = ''
  try {
    await axios.post('/api/admin/smtp/config', config.value, {
      headers: authStore.getHeaders()
    })
    message.value = "Configuration saved successfully!"
    smtpNotConfigured.value = false
  } catch (e) {
    error.value = "Save failed: " + (e.response?.data?.detail || e.message)
  } finally {
    loading.value = false
  }
}

const saveServerGroup = async (server) => {
  savingGroup.value = server.server_id
  try {
    await axios.put(`/api/admin/servers/${server.server_id}/group`, {
      group_name: server.editGroup || null
    }, {
      headers: authStore.getHeaders()
    })
    server.group_name = server.editGroup
  } catch (e) {
    if (e.response && e.response.status === 401) {
      authStore.logout()
      router.push('/login')
      return
    }
    alert('Error guardando grupo: ' + (e.response?.data?.detail || e.message))
  } finally {
    savingGroup.value = null
  }
}

const saveServerInterval = async (server) => {
  savingInterval.value = server.server_id
  try {
    await axios.put(`/api/admin/servers/${server.server_id}/config`, {
      report_interval: parseInt(server.editInterval)
    }, {
      headers: authStore.getHeaders()
    })
    server.report_interval = parseInt(server.editInterval)
    alert('Intervalo actualizado. El agente recogerá el cambio en su próximo reporte.')
  } catch (e) {
    if (e.response && e.response.status === 401) {
      authStore.logout()
      router.push('/login')
      return
    }
    alert('Error guardando intervalo: ' + (e.response?.data?.detail || e.message))
  } finally {
    savingInterval.value = null
  }
}

const formatInterval = (seconds) => {
  if (seconds === null || seconds === undefined) return 'Sin configurar'
  if (seconds === 0) return 'Desactivado'
  if (seconds < 60) return `${seconds}s`
  if (seconds < 3600) return `${Math.round(seconds / 60)} min`
  if (seconds < 86400) return `${Math.round(seconds / 3600)} h`
  return `${Math.round(seconds / 86400)} días`
}
</script>

<template>
  <div class="min-h-screen bg-gray-100 dark:bg-gray-900 py-12 px-4 sm:px-6 lg:px-8 transition-colors duration-200">
    <div class="max-w-5xl mx-auto space-y-8">
      <div class="flex items-center justify-between mb-8">
        <h1 class="text-3xl font-bold text-gray-900 dark:text-white">System Configuration</h1>
        <router-link to="/" class="text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300 font-medium flex items-center transition-colors">
          <svg class="h-5 w-5 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 19l-7-7m0 0l7-7m-7 7h18" />
          </svg>
          Back to Dashboard
        </router-link>
      </div>

      <div v-if="smtpNotConfigured" class="bg-yellow-50 dark:bg-yellow-900/30 border border-yellow-200 dark:border-yellow-700 text-yellow-800 dark:text-yellow-200 px-4 py-3 rounded-lg text-sm flex items-start">
        <svg class="h-5 w-5 mr-2 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01M4.93 19h14.14L12 5 4.93 19z" />
        </svg>
        <div>
          <p class="font-medium">No hay configuración SMTP creada.</p>
          <p class="mt-1">Completa los campos de abajo y guarda para habilitar el envío de correos de alerta.</p>
        </div>
      </div>

      <div class="bg-white dark:bg-gray-800 shadow-lg rounded-2xl overflow-hidden border border-gray-100 dark:border-gray-700">
        <div class="px-6 py-4 border-b border-gray-100 dark:border-gray-700 bg-gray-50/50 dark:bg-gray-700/50">
          <h2 class="text-lg font-medium text-gray-900 dark:text-white">SMTP Settings</h2>
          <p class="mt-1 text-sm text-gray-500 dark:text-gray-400">Configure email settings for system alerts.</p>
        </div>

        <div class="p-6">
          <div v-if="message" class="bg-green-50 dark:bg-green-900/30 border border-green-200 dark:border-green-800 text-green-700 dark:text-green-300 px-4 py-3 rounded-md mb-6 text-sm flex items-center">
            <svg class="h-5 w-5 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
            </svg>
            {{ message }}
          </div>
          <div v-if="error" class="bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-800 text-red-700 dark:text-red-300 px-4 py-3 rounded-md mb-6 text-sm flex items-center">
            <svg class="h-5 w-5 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
               <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            {{ error }}
          </div>

          <form @submit.prevent="saveConfig" class="space-y-6">
            <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">SMTP Host</label>
                <input 
                  v-model="config.host" 
                  class="block w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 sm:text-sm transition-colors" 
                  placeholder="smtp.example.com" 
                  required
                >
              </div>
              <div>
                <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Port</label>
                <input 
                  v-model.number="config.port" 
                  type="number" 
                  class="block w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 sm:text-sm transition-colors" 
                  required
                >
              </div>
            </div>

            <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Username</label>
                <input 
                  v-model="config.username" 
                  class="block w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 sm:text-sm transition-colors" 
                  required
                >
              </div>
              <div>
                <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Password</label>
                <input 
                  v-model="config.password" 
                  type="password" 
                  class="block w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 sm:text-sm transition-colors" 
                  placeholder="Leave blank to keep unchanged" 
                >
              </div>
            </div>

            <div>
              <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Sender Email</label>
              <input 
                v-model="config.sender_email" 
                type="email" 
                class="block w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 sm:text-sm transition-colors" 
                required
              >
            </div>

            <div class="flex gap-6">
              <label class="flex items-center space-x-2 cursor-pointer">
                <input v-model="config.use_tls" type="checkbox" class="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded dark:border-gray-600 dark:bg-gray-700">
                <span class="text-sm text-gray-700 dark:text-gray-300">Use TLS</span>
              </label>
              <label class="flex items-center space-x-2 cursor-pointer">
                <input v-model="config.use_ssl" type="checkbox" class="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded dark:border-gray-600 dark:bg-gray-700">
                <span class="text-sm text-gray-700 dark:text-gray-300">Use SSL</span>
              </label>
            </div>

            <div class="pt-4 border-t border-gray-100 dark:border-gray-700 flex justify-end gap-3">
              <button 
                type="button" 
                @click="testConnection" 
                :disabled="loading" 
                class="px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm text-sm font-medium text-gray-700 dark:text-gray-200 bg-white dark:bg-gray-700 hover:bg-gray-50 dark:hover:bg-gray-600 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-colors"
              >
                Test Connection
              </button>
              <button 
                type="submit" 
                :disabled="loading" 
                class="px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 transition-colors"
              >
                <span v-if="loading">Saving...</span>
                <span v-else>Save Configuration</span>
              </button>
            </div>
          </form>
        </div>
      </div>

      <div class="bg-white dark:bg-gray-800 shadow-lg rounded-2xl overflow-hidden border border-gray-100 dark:border-gray-700">
        <div class="px-6 py-4 border-b border-gray-100 dark:border-gray-700 bg-gray-50/50 dark:bg-gray-700/50">
          <h2 class="text-lg font-medium text-gray-900 dark:text-white">Grupos / Proyectos por servidor</h2>
          <p class="mt-1 text-sm text-gray-500 dark:text-gray-400">
            Asigna un grupo o proyecto a cada servidor. Luego podrás filtrar por grupo en el dashboard.
          </p>
        </div>
        <div class="p-6">
          <div v-if="servers.length === 0" class="text-sm text-gray-500 dark:text-gray-400">
            No hay servidores registrados todavía.
          </div>
          <div v-else class="overflow-x-auto">
            <table class="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
              <thead class="bg-gray-50 dark:bg-gray-700">
                <tr>
                  <th class="px-4 py-2 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">Servidor</th>
                  <th class="px-4 py-2 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">Grupo / Proyecto</th>
                  <th class="px-4 py-2 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">Intervalo</th>
                  <th class="px-4 py-2 text-right text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">Acciones</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-gray-200 dark:divide-gray-700">
                <tr v-for="server in servers" :key="server.server_id">
                  <td class="px-4 py-2 text-sm text-gray-900 dark:text-white">
                    <div class="font-mono text-xs text-gray-600 dark:text-gray-300">{{ server.server_id }}</div>
                    <div class="text-xs text-gray-500 dark:text-gray-400" v-if="server.group_name">
                      Actual: {{ server.group_name }}
                    </div>
                  </td>
                  <td class="px-4 py-2">
                    <input
                      v-model="server.editGroup"
                      type="text"
                      class="mt-1 block w-full rounded-md border-gray-300 dark:border-gray-600 shadow-sm focus:border-blue-500 focus:ring-blue-500 dark:bg-gray-700 dark:text-white sm:text-sm"
                      placeholder="Ej: Proyecto 1"
                    >
                  </td>
                  <td class="px-4 py-2">
                    <select
                      v-model="server.editInterval"
                      class="mt-1 block w-full rounded-md border-gray-300 dark:border-gray-600 shadow-sm focus:border-blue-500 focus:ring-blue-500 dark:bg-gray-700 dark:text-white sm:text-sm"
                    >
                      <option v-for="opt in intervalOptions" :key="opt.value" :value="opt.value">
                        {{ opt.label }}
                      </option>
                    </select>
                    <div class="text-xs text-gray-500 mt-1">
                      Actual: {{ server.report_interval }}s
                    </div>
                  </td>
                  <td class="px-4 py-2 text-right space-x-2">
                    <button
                      @click="saveServerGroup(server)"
                      :disabled="savingGroup === server.server_id"
                      class="inline-flex items-center px-3 py-1.5 border border-transparent text-xs font-medium rounded-md shadow-sm text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-50"
                    >
                      <span v-if="savingGroup === server.server_id">...</span>
                      <span v-else>Grp</span>
                    </button>
                    <button
                      @click="saveServerInterval(server)"
                      :disabled="savingInterval === server.server_id"
                      class="inline-flex items-center px-3 py-1.5 border border-transparent text-xs font-medium rounded-md shadow-sm text-white bg-green-600 hover:bg-green-700 disabled:opacity-50"
                    >
                      <span v-if="savingInterval === server.server_id">...</span>
                      <span v-else>Int</span>
                    </button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
