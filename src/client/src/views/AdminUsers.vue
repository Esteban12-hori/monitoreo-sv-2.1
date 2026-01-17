<template>
  <div class="space-y-6">
    <div class="flex justify-between items-center">
      <div class="flex items-center gap-3">
        <button
          @click="goBack"
          class="inline-flex items-center px-3 py-1.5 border border-gray-300 dark:border-gray-600 rounded-md text-xs font-medium text-gray-700 dark:text-gray-200 bg-white dark:bg-gray-700 hover:bg-gray-50 dark:hover:bg-gray-600 transition-colors"
        >
          <svg class="h-4 w-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 19l-7-7m0 0l7-7m-7 7h18" />
          </svg>
          Volver
        </button>
        <h1 class="text-3xl font-bold text-gray-900 dark:text-white">Gestión de Usuarios</h1>
      </div>
      <button 
        @click="openCreateModal"
        class="bg-indigo-600 hover:bg-indigo-700 text-white px-4 py-2 rounded-md flex items-center gap-2 transition-colors"
      >
        <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
          <path fill-rule="evenodd" d="M10 3a1 1 0 011 1v5h5a1 1 0 110 2h-5v5a1 1 0 11-2 0v-5H4a1 1 0 110-2h5V4a1 1 0 011-1z" clip-rule="evenodd" />
        </svg>
        Nuevo Usuario
      </button>
    </div>

    <!-- Lista de Usuarios -->
    <div class="bg-white dark:bg-gray-800 shadow rounded-lg overflow-hidden">
      <table class="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
        <thead class="bg-gray-50 dark:bg-gray-700">
          <tr>
            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">Usuario</th>
            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">Rol</th>
            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">Estado</th>
            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">Servidores</th>
            <th class="px-6 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">Acciones</th>
          </tr>
        </thead>
        <tbody class="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
          <tr v-for="user in users" :key="user.id">
            <td class="px-6 py-4 whitespace-nowrap">
              <div class="flex items-center">
                <div class="h-10 w-10 rounded-full bg-indigo-100 dark:bg-indigo-900 flex items-center justify-center text-indigo-600 dark:text-indigo-300 font-bold">
                  {{ user.name ? user.name.charAt(0).toUpperCase() : user.email.charAt(0).toUpperCase() }}
                </div>
                <div class="ml-4">
                  <div class="text-sm font-medium text-gray-900 dark:text-white">{{ user.name || 'Sin nombre' }}</div>
                  <div class="text-sm text-gray-500 dark:text-gray-400">{{ user.email }}</div>
                </div>
              </div>
            </td>
            <td class="px-6 py-4 whitespace-nowrap">
              <span v-if="user.is_admin" class="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200">
                Administrador
              </span>
              <span v-else class="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200">
                Usuario
              </span>
            </td>
            <td class="px-6 py-4 whitespace-nowrap">
              <span
                class="px-2 inline-flex text-xs leading-5 font-semibold rounded-full"
                :class="user.is_blocked ? 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200' : 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900 dark:text-emerald-200'"
              >
                {{ user.is_blocked ? 'Bloqueado' : 'Activo' }}
              </span>
            </td>
            <td class="px-6 py-4">
              <button 
                @click="openAssignModal(user)"
                class="text-indigo-600 dark:text-indigo-400 hover:text-indigo-900 dark:hover:text-indigo-300 text-sm font-medium"
              >
                Gestionar Acceso
              </button>
            </td>
            <td class="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
              <button 
                @click="toggleBlock(user)"
                class="text-xs px-3 py-1 rounded-full border mr-3"
                :class="user.is_blocked ? 'border-emerald-500 text-emerald-600 hover:bg-emerald-50 dark:text-emerald-300 dark:border-emerald-400' : 'border-red-500 text-red-600 hover:bg-red-50 dark:text-red-300 dark:border-red-400'"
                :disabled="user.id === currentUser.user_id"
              >
                {{ user.is_blocked ? 'Desbloquear' : 'Bloquear' }}
              </button>
              <button 
                @click="deleteUser(user)"
                class="text-red-600 hover:text-red-900 dark:hover:text-red-400 ml-4"
                :disabled="user.id === currentUser.user_id"
                :class="{'opacity-50 cursor-not-allowed': user.id === currentUser.user_id}"
              >
                Eliminar
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Modal Crear Usuario -->
    <div v-if="showCreateModal" class="fixed inset-0 z-50 overflow-y-auto" aria-labelledby="modal-title" role="dialog" aria-modal="true">
      <!-- Backdrop with blur -->
      <div class="fixed inset-0 bg-gray-900/50 dark:bg-black/70 backdrop-blur-sm transition-opacity" @click="showCreateModal = false"></div>

      <div class="flex min-h-full items-end justify-center p-4 text-center sm:items-center sm:p-0">
        <div class="relative transform overflow-hidden rounded-2xl bg-white dark:bg-gray-800 text-left shadow-2xl ring-1 ring-black/5 transition-all sm:my-8 sm:w-full sm:max-w-lg border border-gray-100 dark:border-gray-700">
          <div class="bg-white dark:bg-gray-800 px-4 pt-5 pb-4 sm:p-6 sm:pb-4">
            <h3 class="text-lg leading-6 font-semibold text-gray-900 dark:text-white flex items-center gap-2" id="modal-title">
              <div class="p-1.5 bg-indigo-100 dark:bg-indigo-900/30 rounded-lg text-indigo-600 dark:text-indigo-400">
                <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M18 9v3m0 0v3m0-3h3m-3 0h-3m-2-5a4 4 0 11-8 0 4 4 0 018 0zM3 20a6 6 0 0112 0v1H3v-1z" />
                </svg>
              </div>
              Crear Nuevo Usuario
            </h3>
            <div class="mt-6 space-y-4">
              <div>
                <label class="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">Nombre</label>
                <input v-model="newUser.name" type="text" class="block w-full rounded-lg border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm py-2">
              </div>
              <div>
                <label class="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">Email</label>
                <input v-model="newUser.email" type="email" class="block w-full rounded-lg border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm py-2">
              </div>
              <div>
                <label class="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">Contraseña</label>
                <div class="relative">
                  <input 
                    v-model="newUser.password"
                    :type="showNewUserPassword ? 'text' : 'password'"
                    class="block w-full rounded-lg border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm py-2 pr-10"
                  >
                  <button
                    type="button"
                    class="absolute inset-y-0 right-0 px-3 flex items-center text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 focus:outline-none"
                    @click="showNewUserPassword = !showNewUserPassword"
                  >
                    <svg v-if="!showNewUserPassword" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.477 0 8.268 2.943 9.542 7-1.274 4.057-5.065 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                    </svg>
                    <svg v-else class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13.875 18.825A10.05 10.05 0 0112 19c-4.477 0-8.268-2.943-9.542-7a9.956 9.956 0 012.242-3.772M6.228 6.228A9.956 9.956 0 0112 5c4.477 0 8.268 2.943 9.542 7a9.965 9.965 0 01-4.043 5.197M15 12a3 3 0 00-3-3m0 0a3 3 0 00-2.121.879M12 9l-2-2m0 0L4 4m6 3l2-2m0 0l6-3m-6 3l3 3" />
                    </svg>
                  </button>
                </div>
              </div>
              <div class="flex items-center pt-2">
                <input v-model="newUser.is_admin" type="checkbox" class="h-4 w-4 text-indigo-600 focus:ring-indigo-500 border-gray-300 rounded cursor-pointer">
                <label class="ml-2 block text-sm text-gray-900 dark:text-gray-300 cursor-pointer" @click="newUser.is_admin = !newUser.is_admin">
                  Es Administrador
                </label>
              </div>
            </div>
          </div>
          <div class="bg-gray-50 dark:bg-gray-700/50 px-4 py-3 sm:px-6 sm:flex sm:flex-row-reverse border-t border-gray-100 dark:border-gray-700">
            <button 
              @click="createUser" 
              type="button" 
              class="w-full inline-flex justify-center rounded-lg border border-transparent shadow-sm px-4 py-2 bg-indigo-600 text-base font-medium text-white hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 sm:ml-3 sm:w-auto sm:text-sm transition-colors"
            >
              Crear Usuario
            </button>
            <button 
              @click="showCreateModal = false" 
              type="button" 
              class="mt-3 w-full inline-flex justify-center rounded-lg border border-gray-300 shadow-sm px-4 py-2 bg-white text-base font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 sm:mt-0 sm:ml-3 sm:w-auto sm:text-sm dark:bg-gray-800 dark:text-gray-200 dark:border-gray-600 dark:hover:bg-gray-700 transition-colors"
            >
              Cancelar
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Modal Asignar Servidores -->
    <div
      v-if="showAssignModal"
      class="fixed inset-0 z-50 overflow-y-auto"
      role="dialog"
      aria-modal="true"
    >
      <!-- Backdrop with blur -->
      <div
        class="fixed inset-0 bg-gray-900/50 dark:bg-black/70 backdrop-blur-sm transition-opacity"
        @click="showAssignModal = false"
      ></div>

      <div class="flex min-h-full items-end justify-center p-4 text-center sm:items-center sm:p-0">
        <div class="relative transform overflow-hidden rounded-2xl bg-white dark:bg-gray-800 text-left shadow-2xl ring-1 ring-black/5 transition-all sm:my-8 sm:w-full sm:max-w-2xl border border-gray-100 dark:border-gray-700">
          <div class="bg-white dark:bg-gray-800 px-4 pt-5 pb-4 sm:p-6">
            <h3 class="text-lg leading-6 font-semibold text-gray-900 dark:text-white flex items-center gap-2">
              <div class="p-1.5 bg-blue-100 dark:bg-blue-900/30 rounded-lg text-blue-600 dark:text-blue-400">
                <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
                </svg>
              </div>
              Asignar Servidores a {{ selectedUser?.name }}
            </h3>
            <p class="mt-2 text-sm text-gray-500 dark:text-gray-400">
              Selecciona qué servidores puede ver este usuario y si debe recibir alertas de ellos.
            </p>
            
            <div class="mt-6 max-h-[60vh] overflow-y-auto border border-gray-200 dark:border-gray-700 rounded-lg">
              <table class="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
                <thead class="bg-gray-50 dark:bg-gray-700/50 sticky top-0 z-10">
                  <tr>
                    <th class="px-4 py-3 text-left text-xs font-semibold text-gray-500 dark:text-gray-300 uppercase tracking-wider">Servidor</th>
                    <th class="px-4 py-3 text-center text-xs font-semibold text-gray-500 dark:text-gray-300 uppercase tracking-wider">Acceso</th>
                    <th class="px-4 py-3 text-center text-xs font-semibold text-gray-500 dark:text-gray-300 uppercase tracking-wider">Recibir Alertas</th>
                  </tr>
                </thead>
                <tbody class="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
                  <tr v-for="server in allServers" :key="server.server_id" class="hover:bg-gray-50 dark:hover:bg-gray-700/30 transition-colors">
                    <td class="px-4 py-3 text-sm text-gray-900 dark:text-white">
                      <div class="font-medium">{{ server.server_id }}</div>
                      <div v-if="server.group_name" class="text-xs text-gray-500">{{ server.group_name }}</div>
                    </td>
                    <td class="px-4 py-3 text-center">
                      <input 
                        type="checkbox" 
                        :checked="isAssigned(server.server_id)"
                        @change="toggleAccess(server.server_id)"
                        class="h-4 w-4 text-indigo-600 focus:ring-indigo-500 border-gray-300 rounded cursor-pointer"
                      >
                    </td>
                    <td class="px-4 py-3 text-center">
                      <input 
                        type="checkbox" 
                        :disabled="!isAssigned(server.server_id)"
                        :checked="receivesAlerts(server.server_id)"
                        @change="toggleAlerts(server.server_id)"
                        class="h-4 w-4 text-indigo-600 focus:ring-indigo-500 border-gray-300 rounded disabled:opacity-50 cursor-pointer disabled:cursor-not-allowed"
                      >
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
          <div class="bg-gray-50 dark:bg-gray-700/50 px-4 py-3 sm:px-6 sm:flex sm:flex-row-reverse border-t border-gray-100 dark:border-gray-700">
            <button 
              @click="saveAssignments" 
              class="w-full inline-flex justify-center rounded-lg border border-transparent shadow-sm px-4 py-2 bg-indigo-600 text-base font-medium text-white hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 sm:ml-3 sm:w-auto sm:text-sm transition-colors"
            >
              Guardar Cambios
            </button>
            <button 
              @click="showAssignModal = false" 
              class="mt-3 w-full inline-flex justify-center rounded-lg border border-gray-300 shadow-sm px-4 py-2 bg-white text-base font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 sm:mt-0 sm:ml-3 sm:w-auto sm:text-sm dark:bg-gray-800 dark:text-gray-200 dark:border-gray-600 dark:hover:bg-gray-700 transition-colors"
            >
              Cerrar
            </button>
          </div>
        </div>
      </div>
    </div>

  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import axios from 'axios'

const router = useRouter()
const authStore = useAuthStore()
const currentUser = computed(() => authStore.user)

const users = ref([])
const allServers = ref([])
const showCreateModal = ref(false)
const showAssignModal = ref(false)
const showNewUserPassword = ref(false)
const selectedUser = ref(null)

// Estado local de asignaciones para el modal
const tempAssignments = ref({}) // { server_id: { assigned: bool, alerts: bool } }

const newUser = ref({
  name: '',
  email: '',
  password: '',
  is_admin: false
})

const goBack = () => {
  router.push('/dashboard')
}

const API_BASE = '' // Use relative path to leverage Vite proxy

const fetchUsers = async () => {
  try {
    const res = await axios.get(`${API_BASE}/api/admin/users`, { headers: authStore.getHeaders() })
    users.value = res.data
  } catch (error) {
    console.error('Error fetching users:', error)
    if (error.response && error.response.status === 401) {
      authStore.logout()
      router.push('/login')
    }
  }
}

const fetchServers = async () => {
  try {
    const res = await axios.get(`${API_BASE}/api/servers`, { headers: authStore.getHeaders() })
    allServers.value = res.data
  } catch (error) {
    console.error('Error fetching servers:', error)
    if (error.response && error.response.status === 401) {
      authStore.logout()
      router.push('/login')
    }
  }
}

const openCreateModal = () => {
  newUser.value = { name: '', email: '', password: '', is_admin: false }
  showCreateModal.value = true
}

const createUser = async () => {
  try {
    await axios.post(`${API_BASE}/api/admin/users`, {
      ...newUser.value,
      receive_alerts: false,
      must_change_password: true
    }, { headers: authStore.getHeaders() })
    showCreateModal.value = false
    await fetchUsers()
  } catch (error) {
    alert('Error creando usuario: ' + (error.response?.data?.detail || error.message))
  }
}

const deleteUser = async (user) => {
  if (!confirm(`¿Estás seguro de eliminar al usuario ${user.email}?`)) return
  try {
    await axios.delete(`${API_BASE}/api/admin/users/${user.id}`, { headers: authStore.getHeaders() })
    await fetchUsers()
  } catch (error) {
    alert('Error eliminando usuario')
  }
}

const toggleBlock = async (user) => {
  const action = user.is_blocked ? 'desbloquear' : 'bloquear'
  if (!confirm(`¿Seguro que quieres ${action} al usuario ${user.email}?`)) return
  try {
    const payload = {
      is_blocked: !user.is_blocked
    }
    await axios.put(`${API_BASE}/api/admin/users/${user.id}`, payload, { headers: authStore.getHeaders() })
    await fetchUsers()
  } catch (error) {
    alert('Error actualizando estado del usuario: ' + (error.response?.data?.detail || error.message))
  }
}

const openAssignModal = async (user) => {
  selectedUser.value = user
  // Reset temp assignments
  tempAssignments.value = {}
  allServers.value.forEach(s => {
    tempAssignments.value[s.server_id] = { assigned: false, alerts: false }
  })

  // Fetch current assignments
  try {
    const res = await axios.get(`${API_BASE}/api/admin/users/${user.id}/servers`, { headers: authStore.getHeaders() })
    res.data.forEach(assignment => {
      if (tempAssignments.value[assignment.server_id]) {
        tempAssignments.value[assignment.server_id].assigned = true
        tempAssignments.value[assignment.server_id].alerts = assignment.receive_alerts
      }
    })
    showAssignModal.value = true
  } catch (error) {
    console.error('Error fetching assignments', error)
  }
}

const isAssigned = (serverId) => tempAssignments.value[serverId]?.assigned
const receivesAlerts = (serverId) => tempAssignments.value[serverId]?.alerts

const toggleAccess = (serverId) => {
  const current = tempAssignments.value[serverId]
  current.assigned = !current.assigned
  if (!current.assigned) current.alerts = false
}

const toggleAlerts = (serverId) => {
  const current = tempAssignments.value[serverId]
  if (current.assigned) {
    current.alerts = !current.alerts
  }
}

const saveAssignments = async () => {
  const payload = {
    assignments: Object.entries(tempAssignments.value)
      .filter(([_, val]) => val.assigned)
      .map(([serverId, val]) => ({
        server_id: serverId,
        receive_alerts: val.alerts
      }))
  }
  
  try {
    await axios.post(`${API_BASE}/api/admin/users/${selectedUser.value.id}/servers`, payload, { headers: authStore.getHeaders() })
    showAssignModal.value = false
    alert('Asignaciones guardadas correctamente')
  } catch (error) {
    alert('Error guardando asignaciones')
  }
}

onMounted(() => {
  fetchUsers()
  fetchServers()
})
</script>
