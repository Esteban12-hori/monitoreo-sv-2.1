<script setup>
import { ref, onMounted, onUnmounted, computed } from 'vue'
import { useAuthStore } from '../stores/auth'
import { useRouter } from 'vue-router'
import axios from 'axios'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend
} from 'chart.js'
import { Line } from 'vue-chartjs'

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend
)

const authStore = useAuthStore()
const router = useRouter()
const servers = ref([])
const metrics = ref({})
const loading = ref(true)
const pollInterval = ref(null)
const smtpWarning = ref(false)

// Filtering state
const timeRange = ref('1') // hours
const selectedGroup = ref('all')
const showInstallModal = ref(false)
const installOS = ref('linux')

const groups = computed(() => {
  const g = new Set(servers.value.map(s => s.group_name).filter(Boolean))
  return Array.from(g)
})

const installCommand = computed(() => {
  const origin = window.location.origin
  if (installOS.value === 'windows') {
    return `curl ${origin}/api/agent/install -o install.py; python install.py`
  }
  return `curl -sSL ${origin}/api/agent/install | python3 -`
})

const copyInstallCommand = () => {
  navigator.clipboard.writeText(installCommand.value)
  alert('Comando copiado al portapapeles')
}

const filteredServers = computed(() => {
  if (selectedGroup.value === 'all') return servers.value
  return servers.value.filter(s => s.group_name === selectedGroup.value)
})

const checkSmtpConfig = async () => {
  if (!authStore.isAdmin) return
  try {
    await axios.get('/api/admin/smtp/config', {
      headers: authStore.getHeaders()
    })
  } catch (e) {
    if (e.response && e.response.status === 404) {
      smtpWarning.value = true
    }
  }
}

const fetchServers = async () => {
  try {
    const res = await axios.get('/api/servers', { headers: authStore.getHeaders() })
    servers.value = res.data
    // Fetch initial metrics for each server
    refetchAll()
  } catch (error) {
    console.error("Error fetching servers", error)
  } finally {
    loading.value = false
  }
}

const refetchAll = () => {
  servers.value.forEach(s => fetchMetrics(s.server_id))
}

const fetchMetrics = async (serverId) => {
  try {
    // Adjust limit based on timeRange
    let limit = 100 // default for small ranges or overview
    if (timeRange.value === '1') limit = 720   // ~1h at 5s
    if (timeRange.value === '6') limit = 2000  // truncated
    if (timeRange.value === '24') limit = 3000 // truncated

    const res = await axios.get(`/api/metrics/history?server_id=${serverId}&limit=${limit}&hours=${timeRange.value}`, { headers: authStore.getHeaders() })
    if (res.data && res.data.length > 0) {
      metrics.value[serverId] = {
        latest: res.data[res.data.length - 1], // Latest is last
        history: res.data
      }
    }
  } catch (error) {
    console.error(`Error fetching metrics for ${serverId}`, error)
  }
}

const exportData = async (format, serverId = null) => {
  try {
    const params = new URLSearchParams({
      format: format,
      hours: timeRange.value
    })
    if (serverId) {
      params.append('server_id', serverId)
    }

    const response = await axios.get(`/api/metrics/export?${params.toString()}`, {
      headers: authStore.getHeaders(),
      responseType: 'blob'
    })
    
    const url = window.URL.createObjectURL(new Blob([response.data]))
    const link = document.createElement('a')
    link.href = url
    const ext = format === 'csv' ? 'csv' : 'json'
    const prefix = serverId ? `metrics_${serverId}` : 'metrics_export'
    link.setAttribute('download', `${prefix}_${new Date().toISOString()}.${ext}`)
    document.body.appendChild(link)
    link.click()
    link.remove()
  } catch (error) {
    console.error("Export failed", error)
    alert("Export failed")
  }
}

const logout = () => {
  authStore.logout()
  router.push('/login')
}

onMounted(() => {
  fetchServers()
  if (authStore.isAdmin) {
    checkSmtpConfig()
  }
  pollInterval.value = setInterval(() => {
    refetchAll()
  }, 5000)
})

onUnmounted(() => {
  if (pollInterval.value) clearInterval(pollInterval.value)
})

// Chart Config Helper
const getChartData = (serverId, type) => {
  const data = metrics.value[serverId]?.history || []
  const labels = data.map(d => new Date(d.ts).toLocaleTimeString())
  
  let dataset = []
  if (type === 'cpu') {
    dataset = data.map(d => d.cpu.total)
  } else if (type === 'memory') {
    dataset = data.map(d => (d.memory.used / d.memory.total) * 100)
  } else if (type === 'disk') {
    dataset = data.map(d => d.disk.percent)
  }

  return {
    labels,
    datasets: [{
      label: type.toUpperCase() + ' %',
      data: dataset,
      borderColor: type === 'cpu' ? '#3B82F6' : type === 'memory' ? '#10B981' : '#F59E0B',
      tension: 0.4,
      pointRadius: 0
    }]
  }
}

const chartOptions = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: { display: false }
  },
  scales: {
    x: { display: false },
    y: { display: false, min: 0, max: 100 }
  }
}

const formatBytes = (bytes, decimals = 2) => {
  if (!+bytes) return '0 Bytes'
  const k = 1024
  const dm = decimals < 0 ? 0 : decimals
  const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(dm))} ${sizes[i]}`
}

const formatUptime = (seconds) => {
  if (!seconds) return '-'
  const d = Math.floor(seconds / (3600 * 24))
  const h = Math.floor(seconds % (3600 * 24) / 3600)
  const m = Math.floor(seconds % 3600 / 60)
  let s = ''
  if (d > 0) s += `${d}d `
  if (h > 0) s += `${h}h `
  s += `${m}m`
  return s || '0m'
}
</script>

<template>
  <div class="min-h-screen bg-gray-100 dark:bg-gray-900 flex flex-col font-sans text-gray-900 dark:text-gray-100 transition-colors duration-200">
    <!-- Top Navigation -->
    <header class="bg-white dark:bg-gray-800 shadow-sm z-10 border-b border-transparent dark:border-gray-700 transition-colors duration-200">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div class="flex justify-between h-16">
          <div class="flex items-center">
            <svg class="h-8 w-8 text-blue-600 dark:text-blue-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
            </svg>
            <span class="ml-2 text-xl font-bold tracking-tight text-gray-900 dark:text-white">MonitorIntegral</span>
          </div>
          <div class="flex items-center space-x-4">
            <router-link v-if="authStore.isAdmin" to="/admin/users" class="text-sm font-medium text-gray-700 dark:text-gray-200 hover:text-blue-600 dark:hover:text-blue-400 mr-2">
              Users
            </router-link>
            <div class="flex flex-col items-end">
              <span class="text-sm font-medium text-gray-700 dark:text-gray-200">{{ authStore.user?.name || authStore.user?.email }}</span>
              <span class="text-xs text-gray-500 dark:text-gray-400" v-if="authStore.isAdmin">Administrator</span>
            </div>
            <button @click="logout" class="text-gray-500 dark:text-gray-400 hover:text-red-600 dark:hover:text-red-400 transition-colors">
              <svg class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
              </svg>
            </button>
          </div>
        </div>
      </div>
    </header>

    <!-- Main Content -->
    <main class="flex-1 overflow-y-auto p-4 sm:p-8">
      <div class="max-w-7xl mx-auto">
        <div class="flex justify-between items-center mb-6">
          <h1 class="text-2xl font-bold text-gray-800 dark:text-white">Server Overview</h1>
          <div class="flex space-x-2" v-if="authStore.isAdmin">
             <router-link to="/setup" class="px-4 py-2 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm text-sm font-medium text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors">
               Settings
             </router-link>
          </div>
        </div>

        <div v-if="smtpWarning" class="mb-4 bg-yellow-50 dark:bg-yellow-900/30 border border-yellow-200 dark:border-yellow-700 text-yellow-800 dark:text-yellow-200 px-4 py-3 rounded-2xl text-sm flex items-start">
          <svg class="h-5 w-5 mr-2 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01M4.93 19h14.14L12 5 4.93 19z" />
          </svg>
          <div>
            <p class="font-medium">SMTP no está configurado.</p>
            <p class="mt-1">Las alertas por correo no se enviarán hasta que completes la configuración en Settings.</p>
          </div>
        </div>

        <!-- Filter Bar -->
        <div class="mb-6 bg-white dark:bg-gray-800 p-3 sm:p-4 rounded-2xl shadow-sm border border-gray-100 dark:border-gray-700 flex flex-col md:flex-row gap-4 justify-between items-start md:items-center transition-colors duration-200">
          <div class="flex flex-col sm:flex-row gap-3 sm:gap-4 w-full md:w-auto">
            <div class="relative w-full sm:w-48">
              <label class="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1 uppercase tracking-wider">Grupo</label>
              <select v-model="selectedGroup" class="block w-full pl-3 pr-8 py-2 text-sm border-gray-300 dark:border-gray-600 bg-gray-50 dark:bg-gray-700 text-gray-900 dark:text-white rounded-lg focus:outline-none focus:ring-blue-500 focus:border-blue-500">
                <option value="all">Todos los grupos</option>
                <option v-for="g in groups" :key="g" :value="g">{{ g }}</option>
              </select>
            </div>
            <div class="relative w-full sm:w-48">
               <label class="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1 uppercase tracking-wider">Rango de tiempo</label>
               <select v-model="timeRange" @change="refetchAll" class="block w-full pl-3 pr-8 py-2 text-sm border-gray-300 dark:border-gray-600 bg-gray-50 dark:bg-gray-700 text-gray-900 dark:text-white rounded-lg focus:outline-none focus:ring-blue-500 focus:border-blue-500">
                 <option value="1">Última hora</option>
                 <option value="6">Últimas 6 horas</option>
                 <option value="24">Últimas 24 horas</option>
               </select>
            </div>
          </div>
          <div class="flex flex-row items-center justify-between w-full md:w-auto gap-4 border-t md:border-t-0 border-gray-100 dark:border-gray-700 pt-3 md:pt-0">
            <div class="text-sm text-gray-500 dark:text-gray-400 font-medium">
              {{ filteredServers.length }} servidores
            </div>
            <div class="flex items-center space-x-2">
               <button @click="showInstallModal = true" class="px-3 py-2 bg-indigo-600 border border-indigo-600 rounded-lg shadow-sm text-xs font-medium text-white hover:bg-indigo-700 flex items-center transition-colors" title="Add Server">
                 <svg class="h-4 w-4 mr-1.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                   <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
                 </svg>
                 Add Server
               </button>
               <button @click="exportData('csv')" class="px-3 py-2 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg shadow-sm text-xs font-medium text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-600 flex items-center transition-colors" title="Export CSV">
                 <svg class="h-4 w-4 mr-1.5 text-green-600 dark:text-green-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                   <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                 </svg>
                 CSV
               </button>
               <button @click="exportData('json')" class="px-3 py-2 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg shadow-sm text-xs font-medium text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-600 flex items-center transition-colors" title="Export JSON">
                 <svg class="h-4 w-4 mr-1.5 text-yellow-600 dark:text-yellow-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                   <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" />
                 </svg>
                 JSON
               </button>
            </div>
          </div>
        </div>

        <div v-if="loading" class="flex justify-center py-12">
          <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 dark:border-blue-400"></div>
        </div>

        <div v-else-if="servers.length === 0" class="text-center py-12 bg-white dark:bg-gray-800 rounded-2xl shadow dark:border dark:border-gray-700 transition-colors duration-200">
          <svg class="mx-auto h-12 w-12 text-gray-400 dark:text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 12h14M5 12a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v4a2 2 0 01-2 2M5 12a2 2 0 01-2 2v4a2 2 0 012 2h14a2 2 0 012-2v-4a2 2 0 01-2-2m-2-4h.01M17 16h.01" />
          </svg>
          <h3 class="mt-2 text-sm font-medium text-gray-900 dark:text-white">No hay servidores monitoreados todavía</h3>
          <p class="mt-1 text-sm text-gray-500 dark:text-gray-400">Instala el agente en un servidor para empezar a ver métricas.</p>

          <div v-if="authStore.isAdmin" class="mt-6 max-w-2xl mx-auto text-left">
            <h4 class="text-sm font-semibold text-gray-900 dark:text-white mb-2">Instalación rápida del agente</h4>
            <p class="text-sm text-gray-500 dark:text-gray-400 mb-3">
              Ejecuta estos comandos en tu servidor Linux o Windows Server que quieras monitorear.
            </p>
            <div class="grid gap-4 md:grid-cols-2">
              <div class="bg-gray-50 dark:bg-gray-900/40 border border-gray-200 dark:border-gray-700 rounded-xl p-4">
                <div class="text-xs font-medium text-gray-500 dark:text-gray-400 mb-2">Linux (incluido Linux Server)</div>
                <pre class="text-xs bg-gray-900 text-gray-100 rounded-lg px-3 py-2 overflow-x-auto"><code>bash agent/python/quick_install.sh</code></pre>
              </div>
              <div class="bg-gray-50 dark:bg-gray-900/40 border border-gray-200 dark:border-gray-700 rounded-xl p-4">
                <div class="text-xs font-medium text-gray-500 dark:text-gray-400 mb-2">Windows / Windows Server</div>
                <pre class="text-xs bg-gray-900 text-gray-100 rounded-lg px-3 py-2 overflow-x-auto"><code>agent\python\quick_install.bat</code></pre>
              </div>
            </div>
          </div>
        </div>

        <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          <div v-for="server in filteredServers" :key="server.server_id" 
               class="bg-white dark:bg-gray-800 rounded-2xl shadow-sm border border-gray-100 dark:border-gray-700 overflow-hidden hover:shadow-md transition-all duration-200 cursor-pointer"
               @click="router.push(`/server/${server.server_id}`)">
            <!-- Card Header -->
            <div class="px-6 py-4 border-b border-gray-50 dark:border-gray-700 flex justify-between items-center bg-gray-50/50 dark:bg-gray-700/50">
              <div class="flex items-center gap-2">
                <div>
                  <h3 class="text-lg font-semibold text-gray-900 dark:text-white truncate" :title="server.server_id">{{ server.server_id }}</h3>
                  <span class="text-xs px-2 py-0.5 rounded-full bg-blue-100 dark:bg-blue-900 text-blue-800 dark:text-blue-200 font-medium" v-if="server.group_name">{{ server.group_name }}</span>
                </div>
              </div>
              <div class="flex items-center gap-3">
                 <!-- Export Actions -->
                 <div class="flex gap-1">
                    <button @click.stop="exportData('csv', server.server_id)" class="text-gray-400 hover:text-green-600 dark:hover:text-green-400 transition-colors" title="Export CSV">
                      <svg class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                         <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                      </svg>
                    </button>
                    <button @click.stop="exportData('json', server.server_id)" class="text-gray-400 hover:text-yellow-600 dark:hover:text-yellow-400 transition-colors" title="Export JSON">
                      <svg class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                         <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" />
                      </svg>
                    </button>
                 </div>
                 <div class="h-2 w-2 rounded-full" :class="metrics[server.server_id] ? 'bg-green-500' : 'bg-gray-300 dark:bg-gray-600'"></div>
              </div>
            </div>

            <!-- Card Body -->
            <div class="p-6 space-y-6" v-if="metrics[server.server_id]">
              <!-- CPU -->
              <div>
                <div class="flex justify-between text-sm mb-1">
                  <span class="text-gray-500 dark:text-gray-400">CPU Usage</span>
                  <span class="font-medium" :class="metrics[server.server_id].latest.cpu.total > 90 ? 'text-red-600 dark:text-red-400' : 'text-gray-900 dark:text-gray-100'">{{ metrics[server.server_id].latest.cpu.total.toFixed(1) }}%</span>
                </div>
                <div class="h-10">
                   <Line :data="getChartData(server.server_id, 'cpu')" :options="chartOptions" />
                </div>
              </div>

              <!-- Memory -->
              <div>
                <div class="flex justify-between text-sm mb-1">
                  <span class="text-gray-500 dark:text-gray-400">Memory</span>
                  <span class="font-medium" :class="(metrics[server.server_id].latest.memory.used / metrics[server.server_id].latest.memory.total) > 0.9 ? 'text-red-600 dark:text-red-400' : 'text-gray-900 dark:text-gray-100'">
                    {{ (metrics[server.server_id].latest.memory.used / 1024 / 1024 / 1024).toFixed(1) }} / 
                    {{ (metrics[server.server_id].latest.memory.total / 1024 / 1024 / 1024).toFixed(1) }} GB
                  </span>
                </div>
                 <div class="h-10">
                   <Line :data="getChartData(server.server_id, 'memory')" :options="chartOptions" />
                </div>
              </div>
              
              <!-- Disk -->
              <div>
                <div class="flex justify-between text-sm mb-1">
                   <span class="text-gray-500 dark:text-gray-400">Disk</span>
                   <span class="font-medium" :class="metrics[server.server_id].latest.disk.percent > 90 ? 'text-red-600 dark:text-red-400' : 'text-gray-900 dark:text-gray-100'">{{ metrics[server.server_id].latest.disk.percent }}%</span>
                </div>
                <div class="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-1.5">
                  <div class="h-1.5 rounded-full" :class="metrics[server.server_id].latest.disk.percent > 90 ? 'bg-red-500' : 'bg-yellow-500'" :style="{ width: metrics[server.server_id].latest.disk.percent + '%' }"></div>
                </div>
              </div>
              
              <!-- Network -->
              <div>
                <div class="flex justify-between text-sm mb-1">
                  <span class="text-gray-500 dark:text-gray-400">Network</span>
                  <span v-if="metrics[server.server_id].latest.network" class="font-medium text-gray-900 dark:text-gray-100">
                    ▲ {{ formatBytes(metrics[server.server_id].latest.network.bytes_sent || 0) }}
                    /
                    ▼ {{ formatBytes(metrics[server.server_id].latest.network.bytes_recv || 0) }}
                  </span>
                  <span v-else class="font-medium text-gray-400 dark:text-gray-500">-</span>
                </div>
              </div>
              
              <!-- Footer Info -->
              <div class="pt-4 border-t border-gray-50 dark:border-gray-700 text-xs text-gray-400 dark:text-gray-500 flex justify-between items-center">
                <span class="flex items-center gap-2">
                  <span>Docker: {{ metrics[server.server_id].latest.docker.running_containers }} running</span>
                  <span v-if="metrics[server.server_id].latest.uptime">· Uptime: {{ formatUptime(metrics[server.server_id].latest.uptime) }}</span>
                </span>
                <span>Last updated: {{ new Date(metrics[server.server_id].latest.ts).toLocaleTimeString() }}</span>
              </div>
            </div>
            
            <div class="p-6 text-center text-gray-500 dark:text-gray-400 italic" v-else>
              Waiting for data...
            </div>
          </div>
        </div>
      </div>
    </main>

    <!-- Install Modal -->
    <div v-if="showInstallModal" class="fixed inset-0 z-50 overflow-y-auto" aria-labelledby="modal-title" role="dialog" aria-modal="true">
      <div class="fixed inset-0 bg-gray-900/50 dark:bg-black/70 backdrop-blur-sm transition-opacity" @click="showInstallModal = false"></div>

      <div class="flex min-h-full items-end justify-center p-4 text-center sm:items-center sm:p-0">
        <div class="relative transform overflow-hidden rounded-2xl bg-white dark:bg-gray-800 text-left shadow-2xl ring-1 ring-black/5 transition-all sm:my-8 sm:w-full sm:max-w-lg border border-gray-100 dark:border-gray-700">
          <div class="bg-white dark:bg-gray-800 px-4 pt-5 pb-4 sm:p-6 sm:pb-4">
            <div class="sm:flex sm:items-start">
              <div class="mx-auto flex-shrink-0 flex items-center justify-center h-12 w-12 rounded-xl bg-indigo-50 dark:bg-indigo-900/30 sm:mx-0 sm:h-10 sm:w-10 text-indigo-600 dark:text-indigo-400">
                <svg class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                </svg>
              </div>
              <div class="mt-3 text-center sm:mt-0 sm:ml-4 sm:text-left w-full">
                <h3 class="text-lg leading-6 font-semibold text-gray-900 dark:text-white" id="modal-title">Instalar Agente</h3>
                
                <div class="flex space-x-2 mt-4 border-b border-gray-200 dark:border-gray-700">
                   <button 
                     @click="installOS = 'linux'"
                     :class="[installOS === 'linux' ? 'border-indigo-500 text-indigo-600 dark:text-indigo-400' : 'border-transparent text-gray-500 hover:text-gray-700 dark:text-gray-400 hover:border-gray-300', 'whitespace-nowrap py-2 px-4 border-b-2 font-medium text-sm transition-colors']"
                   >
                     Linux / macOS
                   </button>
                   <button 
                     @click="installOS = 'windows'"
                     :class="[installOS === 'windows' ? 'border-indigo-500 text-indigo-600 dark:text-indigo-400' : 'border-transparent text-gray-500 hover:text-gray-700 dark:text-gray-400 hover:border-gray-300', 'whitespace-nowrap py-2 px-4 border-b-2 font-medium text-sm transition-colors']"
                   >
                     Windows (PowerShell)
                   </button>
                </div>

                <div class="mt-4">
                  <p class="text-sm text-gray-500 dark:text-gray-400 mb-2">
                    Copia y pega este comando en tu terminal {{ installOS === 'windows' ? 'PowerShell' : 'Bash' }}:
                  </p>
                  <div class="relative rounded-lg shadow-sm group">
                    <div class="bg-gray-900 text-gray-100 p-3 rounded-lg text-sm font-mono break-all border border-gray-700 pr-10">
                      {{ installCommand }}
                    </div>
                    <button @click="copyInstallCommand" class="absolute right-2 top-2 text-gray-400 hover:text-white p-1 rounded hover:bg-gray-800 transition-colors" title="Copiar">
                       <svg class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                       </svg>
                    </button>
                  </div>
                  <p class="mt-2 text-xs text-gray-400">
                    <span v-if="installOS === 'windows'">Requiere Python instalado. Ejecutar en PowerShell.</span>
                    <span v-else>Requiere Python 3 instalado.</span>
                    El script detectará el sistema y configurará la persistencia automáticamente.
                  </p>
                </div>
              </div>
            </div>
          </div>
          <div class="bg-gray-50 dark:bg-gray-700/30 px-4 py-3 sm:px-6 sm:flex sm:flex-row-reverse border-t border-gray-100 dark:border-gray-700">
            <button type="button" class="w-full inline-flex justify-center rounded-xl border border-transparent shadow-sm px-4 py-2 bg-indigo-600 text-base font-medium text-white hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 sm:ml-3 sm:w-auto sm:text-sm transition-colors" @click="copyInstallCommand">
              Copiar Comando
            </button>
            <button type="button" class="mt-3 w-full inline-flex justify-center rounded-xl border border-gray-300 dark:border-gray-600 shadow-sm px-4 py-2 bg-white dark:bg-gray-800 text-base font-medium text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 sm:mt-0 sm:ml-3 sm:w-auto sm:text-sm transition-colors" @click="showInstallModal = false">
              Cerrar
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
