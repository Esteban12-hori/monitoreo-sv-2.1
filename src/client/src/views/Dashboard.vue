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
  BarElement,
  Title,
  Tooltip,
  Legend,
  Filler
} from 'chart.js'
import { Line, Bar } from 'vue-chartjs'

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Legend,
  Filler
)

const authStore = useAuthStore()
const router = useRouter()
const servers = ref([])
const metrics = ref({})
const monitoringStats = ref({ by_app: [], by_server: [] })
const loading = ref(true)
const pollInterval = ref(null)
const smtpWarning = ref(false)

// Filtering state
const timeRange = ref('1')
const selectedGroup = ref('all')
const showInstallModal = ref(false)
const installOS = ref('linux')
const refreshIntervalKey = ref('realtime')
const visibleMetrics = ref({
  cpu: true,
  memory: true,
  disk: true,
  network: true
})

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
    } else if (e.response && e.response.status === 401) {
       authStore.logout()
       router.push('/login')
    }
  }
}

const fetchServers = async () => {
  try {
    const res = await axios.get('/api/servers', { headers: authStore.getHeaders() })
    servers.value = res.data
    refetchAll()
  } catch (error) {
    console.error("Error fetching servers", error)
    if (error.response && error.response.status === 401) {
       authStore.logout()
       router.push('/login')
    }
  } finally {
    loading.value = false
  }
}

const fetchMonitoringStats = async () => {
  try {
    const res = await axios.get('/api/data-monitoring/stats', { headers: authStore.getHeaders() })
    monitoringStats.value = res.data
  } catch (error) {
    console.error("Error fetching monitoring stats", error)
  }
}

const refetchAll = () => {
  filteredServers.value.forEach(s => fetchMetrics(s.server_id))
  fetchMonitoringStats()
}

const getPollIntervalMs = () => {
  if (refreshIntervalKey.value === 'realtime') return 5000
  if (refreshIntervalKey.value === '5m') return 5 * 60 * 1000
  if (refreshIntervalKey.value === '10m') return 10 * 60 * 1000
  if (refreshIntervalKey.value === '30m') return 30 * 60 * 1000
  if (refreshIntervalKey.value === '60m') return 60 * 60 * 1000
  return 15000
}

const startPolling = () => {
  if (pollInterval.value) {
    clearInterval(pollInterval.value)
  }
  const intervalMs = getPollIntervalMs()
  pollInterval.value = setInterval(() => {
    refetchAll()
  }, intervalMs)
}

const stopPolling = () => {
  if (pollInterval.value) {
    clearInterval(pollInterval.value)
    pollInterval.value = null
  }
}

const handleVisibilityChange = () => {
  if (document.hidden) {
    stopPolling()
  } else {
    startPolling()
    refetchAll()
  }
}

const fetchMetrics = async (serverId) => {
  try {
    let limit = 100
    if (timeRange.value === '1') limit = 720
    else if (timeRange.value === '5') limit = 1000
    else if (timeRange.value === '7') limit = 1400
    else if (timeRange.value === '8') limit = 1600
    else if (timeRange.value === '10') limit = 2000
    else if (timeRange.value === '24') limit = 3000

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
  startPolling()
  document.addEventListener('visibilitychange', handleVisibilityChange)
})

onUnmounted(() => {
  if (pollInterval.value) {
    clearInterval(pollInterval.value)
  }
  document.removeEventListener('visibilitychange', handleVisibilityChange)
})


// Monitoring Chart Config
const getMonitoringChartData = computed(() => {
  const data = monitoringStats.value.by_app || []
  return {
    labels: data.map(d => d.label || 'Unknown'),
    datasets: [{
      label: 'Events',
      data: data.map(d => d.count),
      backgroundColor: 'rgba(99, 102, 241, 0.5)',
      borderColor: '#6366f1',
      borderWidth: 1,
      borderRadius: 4
    }]
  }
})

const monitoringChartOptions = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: { display: false },
    title: { display: true, text: 'Events by Application', color: '#9ca3af' }
  },
  scales: {
    y: { 
      beginAtZero: true, 
      grid: { color: '#374151' },
      ticks: { color: '#9ca3af' }
    },
    x: { 
      grid: { display: false },
      ticks: { color: '#9ca3af' }
    }
  }
}

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
      borderColor: type === 'cpu' ? '#22d3ee' : type === 'memory' ? '#34d399' : '#f59e0b',
      backgroundColor: type === 'cpu' ? 'rgba(34, 211, 238, 0.1)' : type === 'memory' ? 'rgba(52, 211, 153, 0.1)' : 'rgba(245, 158, 11, 0.1)',
      fill: true,
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
  },
  elements: {
    line: { borderWidth: 2 }
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

const getServerOs = (server) => {
  const m = metrics.value[server.server_id]?.latest
  if (!m) return 'unknown'
  
  if (m.processes && Array.isArray(m.processes) && m.processes.length > 0) {
      const isWin = m.processes.some(p => p.name.toLowerCase().endsWith('.exe'))
      if (isWin) return 'windows'
      return 'linux'
  }
  return 'unknown'
}
</script>

<template>
  <div class="min-h-screen bg-[#0b1120] flex flex-col font-sans text-gray-100 selection:bg-cyan-500/30">
    <!-- Top Navigation -->
    <header class="bg-[#111827]/80 backdrop-blur-md shadow-sm z-10 border-b border-gray-800 sticky top-0">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div class="flex justify-between h-16">
          <!-- Logo / Brand -->
                <div class="flex-shrink-0 flex items-center gap-3">
                  <div class="h-24 w-24 rounded-lg overflow-hidden">
                    <img src="../assets/logo.png" alt="Logo" class="h-full w-full object-contain" />
                  </div>
                  <span class="text-xl font-bold tracking-tight bg-clip-text text-transparent bg-gradient-to-r from-cyan-400 to-blue-400">UpKeep</span>
                </div>
          <div class="flex items-center space-x-4">
            <div class="flex items-center space-x-2" v-if="authStore.isAdmin">
                 <router-link to="/admin/users" class="text-sm font-medium text-gray-400 hover:text-cyan-400 transition-colors">Users</router-link>
                 <span class="text-gray-600">|</span>
                 <router-link to="/admin/proxmox" class="text-sm font-medium text-gray-400 hover:text-cyan-400 transition-colors">Proxmox</router-link>
                 <span class="text-gray-600">|</span>
                 <router-link to="/admin/monitoring" class="text-sm font-medium text-gray-400 hover:text-cyan-400 transition-colors">Monitoreo</router-link>
                 <span class="text-gray-600">|</span>
                 <router-link to="/admin/logs" class="text-sm font-medium text-gray-400 hover:text-cyan-400 transition-colors">Logs</router-link>
            </div>
            <div class="flex flex-col items-end">
              <span class="text-sm font-medium text-gray-200">{{ authStore.user?.name || authStore.user?.email }}</span>
              <span class="text-xs text-cyan-500/80" v-if="authStore.isAdmin">Administrator</span>
            </div>
            <button @click="logout" class="text-gray-500 hover:text-red-400 transition-colors p-2 rounded-lg hover:bg-gray-800/50">
              <svg class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
              </svg>
            </button>
          </div>
        </div>
      </div>
    </header>

    <!-- Main Content -->
    <main class="flex-1 overflow-y-auto p-4 sm:p-8 custom-scrollbar">
      <div class="max-w-7xl mx-auto">
        <div class="flex justify-between items-center mb-8">
          <h1 class="text-2xl font-bold text-white flex items-center gap-3">
            Server Overview
            <span class="text-xs font-normal px-2.5 py-0.5 rounded-full bg-gray-800 text-gray-400 border border-gray-700">
              {{ filteredServers.length }} Active
            </span>
          </h1>
          <div class="flex space-x-2" v-if="authStore.isAdmin">
             <router-link to="/setup" class="px-4 py-2 bg-[#1f2937] border border-gray-700 rounded-lg shadow-sm text-sm font-medium text-gray-300 hover:bg-gray-800 hover:text-white transition-all">
               Settings
             </router-link>
          </div>
        </div>

        <div v-if="smtpWarning" class="mb-6 bg-yellow-900/20 border border-yellow-500/20 text-yellow-200 px-4 py-3 rounded-xl text-sm flex items-start">
          <svg class="h-5 w-5 mr-2 mt-0.5 text-yellow-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01M4.93 19h14.14L12 5 4.93 19z" />
          </svg>
          <div>
            <p class="font-medium text-yellow-400">SMTP no está configurado.</p>
            <p class="mt-1 opacity-80">Las alertas por correo no se enviarán hasta que completes la configuración en Settings.</p>
          </div>
        </div>

        <!-- Filter Bar -->
        <div class="mb-8 bg-[#111827] p-4 rounded-2xl shadow-lg border border-gray-800 flex flex-col md:flex-row gap-6 justify-between items-start md:items-center">
          <div class="flex flex-col sm:flex-row gap-4 w-full md:w-auto">
            <div class="relative w-full sm:w-48">
              <label class="block text-[10px] font-bold text-gray-500 mb-1 uppercase tracking-widest">Grupo</label>
              <select v-model="selectedGroup" class="block w-full px-3 py-2 text-sm border border-gray-700 bg-gray-900/50 text-gray-200 rounded-lg focus:outline-none focus:ring-1 focus:ring-cyan-500 focus:border-cyan-500 transition-colors">
                <option value="all">Todos los grupos</option>
                <option v-for="g in groups" :key="g" :value="g">{{ g }}</option>
              </select>
            </div>
            <div class="relative w-full sm:w-48">
               <label class="block text-[10px] font-bold text-gray-500 mb-1 uppercase tracking-widest">Rango de tiempo</label>
               <select v-model="timeRange" @change="refetchAll" class="block w-full px-3 py-2 text-sm border border-gray-700 bg-gray-900/50 text-gray-200 rounded-lg focus:outline-none focus:ring-1 focus:ring-cyan-500 focus:border-cyan-500 transition-colors">
                 <option value="1">Última hora</option>
                 <option value="5">Últimas 5 horas</option>
                 <option value="7">Últimas 7 horas</option>
                 <option value="8">Últimas 8 horas</option>
                 <option value="10">Últimas 10 horas</option>
                 <option value="24">Últimas 24 horas</option>
               </select>
            </div>
            <div class="relative w-full sm:w-56">
              <label class="block text-[10px] font-bold text-gray-500 mb-1 uppercase tracking-widest">Actualización</label>
              <select
                v-model="refreshIntervalKey"
                @change="startPolling"
                class="block w-full px-3 py-2 text-sm border border-gray-700 bg-gray-900/50 text-gray-200 rounded-lg focus:outline-none focus:ring-1 focus:ring-cyan-500 focus:border-cyan-500 transition-colors"
              >
                <option value="realtime">Tiempo real (5 s)</option>
                <option value="5m">Cada 5 minutos</option>
                <option value="10m">Cada 10 minutos</option>
                <option value="30m">Cada 30 minutos</option>
                <option value="60m">Cada 60 minutos</option>
              </select>
            </div>
          </div>
          <div class="flex flex-row items-center justify-end w-full md:w-auto gap-3 pt-2 md:pt-0">
               <button @click="showInstallModal = true" class="px-4 py-2 bg-gradient-to-r from-indigo-600 to-indigo-500 border border-indigo-500/50 rounded-lg shadow-lg shadow-indigo-500/20 text-xs font-bold text-white hover:from-indigo-500 hover:to-indigo-400 flex items-center gap-2 transition-all transform hover:scale-105" title="Add Server">
                 <svg class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                   <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
                 </svg>
                 Add Server
               </button>
               <div class="h-8 w-px bg-gray-700 mx-2"></div>
               <button @click="exportData('csv')" class="p-2 bg-gray-800 border border-gray-700 rounded-lg text-gray-400 hover:text-green-400 hover:border-green-500/30 transition-all" title="Export CSV">
                 <svg class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                   <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                 </svg>
               </button>
               <button @click="exportData('json')" class="p-2 bg-gray-800 border border-gray-700 rounded-lg text-gray-400 hover:text-yellow-400 hover:border-yellow-500/30 transition-all" title="Export JSON">
                 <svg class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                   <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" />
                 </svg>
               </button>
          </div>
        </div>

        <!-- Data Monitoring Stats -->
        <div v-if="monitoringStats.by_app.length > 0" class="mb-8">
           <h2 class="text-lg font-bold text-gray-300 mb-4 flex items-center gap-2">
             <svg class="w-5 h-5 text-indigo-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
               <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
             </svg>
             Data Monitoring Overview
           </h2>
           <div class="bg-[#1f2937] p-6 rounded-2xl shadow-lg border border-gray-800 h-72">
              <Bar :data="getMonitoringChartData" :options="monitoringChartOptions" />
           </div>
        </div>

        <div class="mb-6 -mt-2 text-xs text-gray-400 flex flex-wrap items-center gap-3">
          <span class="font-bold text-gray-500 uppercase tracking-wider mr-1">Visible Metrics:</span>
          <button
            type="button"
            @click.stop="visibleMetrics.cpu = !visibleMetrics.cpu"
            :class="[
              'px-3 py-1 rounded-md border text-xs font-medium transition-all',
              visibleMetrics.cpu
                ? 'bg-cyan-500/10 border-cyan-500/50 text-cyan-400'
                : 'bg-gray-800 border-gray-700 text-gray-500 hover:border-gray-600'
            ]"
          >
            CPU
          </button>
          <button
            type="button"
            @click.stop="visibleMetrics.memory = !visibleMetrics.memory"
            :class="[
              'px-3 py-1 rounded-md border text-xs font-medium transition-all',
              visibleMetrics.memory
                ? 'bg-emerald-500/10 border-emerald-500/50 text-emerald-400'
                : 'bg-gray-800 border-gray-700 text-gray-500 hover:border-gray-600'
            ]"
          >
            Memory
          </button>
          <button
            type="button"
            @click.stop="visibleMetrics.disk = !visibleMetrics.disk"
            :class="[
              'px-3 py-1 rounded-md border text-xs font-medium transition-all',
              visibleMetrics.disk
                ? 'bg-amber-500/10 border-amber-500/50 text-amber-400'
                : 'bg-gray-800 border-gray-700 text-gray-500 hover:border-gray-600'
            ]"
          >
            Disk
          </button>
          <button
            type="button"
            @click.stop="visibleMetrics.network = !visibleMetrics.network"
            :class="[
              'px-3 py-1 rounded-md border text-xs font-medium transition-all',
              visibleMetrics.network
                ? 'bg-blue-500/10 border-blue-500/50 text-blue-400'
                : 'bg-gray-800 border-gray-700 text-gray-500 hover:border-gray-600'
            ]"
          >
            Network
          </button>
        </div>

        <div v-if="loading" class="flex justify-center py-24">
          <div class="relative">
            <div class="animate-spin rounded-full h-16 w-16 border-b-2 border-cyan-500"></div>
            <div class="absolute inset-0 flex items-center justify-center">
              <span class="h-2 w-2 bg-cyan-500 rounded-full animate-pulse"></span>
            </div>
          </div>
        </div>

        <div v-else-if="servers.length === 0" class="text-center py-24 bg-[#111827] rounded-3xl shadow-lg border border-gray-800">
          <div class="bg-gray-800/50 w-20 h-20 mx-auto rounded-full flex items-center justify-center mb-6">
            <svg class="h-10 w-10 text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 12h14M5 12a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v4a2 2 0 01-2 2M5 12a2 2 0 01-2 2v4a2 2 0 012 2h14a2 2 0 012-2v-4a2 2 0 01-2-2m-2-4h.01M17 16h.01" />
            </svg>
          </div>
          <h3 class="mt-2 text-lg font-medium text-white">No servers monitored yet</h3>
          <p class="mt-2 text-gray-400 max-w-sm mx-auto">Install the agent on your server to start visualizing metrics in real-time.</p>

          <div v-if="authStore.isAdmin" class="mt-10 max-w-3xl mx-auto text-left px-6">
            <h4 class="text-sm font-bold text-gray-300 mb-4 uppercase tracking-wider text-center">Quick Agent Installation</h4>
            <div class="grid gap-6 md:grid-cols-2">
              <div class="bg-gray-900/50 border border-gray-700 rounded-xl p-6 hover:border-gray-600 transition-colors">
                <div class="flex items-center gap-3 mb-4">
                  <div class="p-2 bg-gray-800 rounded-lg">
                    <svg class="w-5 h-5 text-gray-300" fill="currentColor" viewBox="0 0 24 24"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 17.93c-3.95-.49-7-3.85-7-7.93 0-.62.08-1.21.21-1.79L9 15v1c0 1.1.9 2 2 2v1.93zm6.9-2.54c-.26-.81-1-1.39-1.9-1.39h-1v-3c0-.55-.45-1-1-1H8v-2h2c.55 0 1-.45 1-1V7h2c1.1 0 2-.9 2-2v-.41c2.93 1.19 5 4.06 5 7.41 0 2.08-.8 3.97-2.1 5.39z"/></svg>
                  </div>
                  <div class="text-sm font-medium text-gray-200">Linux / macOS</div>
                </div>
                <div class="relative group">
                   <pre class="text-xs bg-black text-gray-300 rounded-lg p-4 font-mono overflow-x-auto border border-gray-800 group-hover:border-gray-600 transition-colors"><code>bash agent/python/quick_install.sh</code></pre>
                   <div class="absolute right-2 top-2 opacity-0 group-hover:opacity-100 transition-opacity">
                     <span class="text-[10px] text-gray-500">Click to copy</span>
                   </div>
                </div>
              </div>
              <div class="bg-gray-900/50 border border-gray-700 rounded-xl p-6 hover:border-gray-600 transition-colors">
                <div class="flex items-center gap-3 mb-4">
                  <div class="p-2 bg-gray-800 rounded-lg">
                    <svg class="w-5 h-5 text-blue-400" fill="currentColor" viewBox="0 0 24 24"><path d="M3 12V3l9 1v8l-9 1zm10-7.8l9 1.2v6.6l-9 1V4.2zM3 21l9-1.2v-6.6l-9 1V21zm10-7.8l9 1.2v6.6l-9 1v-6.8z"/></svg>
                  </div>
                  <div class="text-sm font-medium text-gray-200">Windows Server</div>
                </div>
                <div class="relative group">
                  <pre class="text-xs bg-black text-gray-300 rounded-lg p-4 font-mono overflow-x-auto border border-gray-800 group-hover:border-gray-600 transition-colors"><code>agent\python\quick_install.bat</code></pre>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          <div v-for="server in filteredServers" :key="server.server_id" 
               class="bg-[#111827] rounded-2xl shadow-lg border border-gray-800 overflow-hidden hover:shadow-cyan-500/10 hover:border-cyan-500/30 transition-all duration-300 cursor-pointer group flex flex-col"
               @click="router.push(`/server/${server.server_id}`)">
            <!-- Card Header -->
            <div class="px-6 py-4 border-b border-gray-800 flex justify-between items-center bg-gray-900/30">
              <div class="flex items-center gap-3 overflow-hidden">
                <div class="h-9 w-9 rounded-lg bg-gray-800 text-gray-400 group-hover:text-cyan-400 group-hover:bg-cyan-500/10 transition-colors flex items-center justify-center overflow-hidden">
                   <img v-if="getServerOs(server) === 'linux'" src="../assets/linux-logo.png" class="w-full h-full object-cover" />
                   <img v-else-if="getServerOs(server) === 'windows'" src="../assets/windows-logo.png" class="w-full h-full object-cover" />
                   <svg v-else class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                     <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 12h14M5 12a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v4a2 2 0 01-2 2M5 12a2 2 0 01-2 2v4a2 2 0 012 2h14a2 2 0 012-2v-4a2 2 0 01-2-2m-2-4h.01M17 16h.01" />
                   </svg>
                </div>
                <div class="min-w-0">
                  <h3 class="text-sm font-bold text-gray-200 truncate group-hover:text-white transition-colors" :title="server.server_id">{{ server.server_id }}</h3>
                  <div class="flex items-center gap-2 mt-0.5">
                    <span class="text-[10px] px-2 py-0.5 rounded bg-gray-800 text-gray-400 border border-gray-700" v-if="server.group_name">{{ server.group_name }}</span>
                    <span class="text-[10px] text-gray-500" v-else>No group</span>
                  </div>
                </div>
              </div>
              <div class="flex items-center gap-3">
                 <div class="relative flex h-3 w-3">
                    <span v-if="metrics[server.server_id]" class="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                    <span class="relative inline-flex rounded-full h-3 w-3" :class="metrics[server.server_id] ? 'bg-emerald-500' : 'bg-gray-600'"></span>
                 </div>
              </div>
            </div>

            <!-- Card Body -->
            <div class="p-6 space-y-6 flex-1" v-if="metrics[server.server_id]">
              <!-- CPU -->
              <div v-if="visibleMetrics.cpu">
                <div class="flex justify-between text-xs mb-2">
                  <span class="text-gray-400 font-medium">CPU Usage</span>
                  <span class="flex items-center gap-2">
                    <span class="font-bold" :class="metrics[server.server_id].latest.cpu.total > 90 ? 'text-red-400' : 'text-cyan-400'">
                      {{ metrics[server.server_id].latest.cpu.total.toFixed(1) }}%
                    </span>
                  </span>
                </div>
                <div class="h-12 relative">
                   <Line :data="getChartData(server.server_id, 'cpu')" :options="chartOptions" />
                </div>
              </div>

              <!-- Memory -->
              <div v-if="visibleMetrics.memory">
                <div class="flex justify-between text-xs mb-2">
                  <span class="text-gray-400 font-medium">Memory</span>
                  <span class="flex items-center gap-2">
                    <span class="font-bold" :class="(metrics[server.server_id].latest.memory.used / metrics[server.server_id].latest.memory.total) > 0.9 ? 'text-red-400' : 'text-emerald-400'">
                      {{ (metrics[server.server_id].latest.memory.used / 1024 / 1024 / 1024).toFixed(1) }} GB
                    </span>
                    <span class="text-gray-600">/</span>
                    <span class="text-gray-500">{{ (metrics[server.server_id].latest.memory.total / 1024 / 1024 / 1024).toFixed(1) }} GB</span>
                  </span>
                </div>
                 <div class="h-12 relative">
                   <Line :data="getChartData(server.server_id, 'memory')" :options="chartOptions" />
                </div>
              </div>
              
              <!-- Disk -->
              <div v-if="visibleMetrics.disk">
                <div class="flex justify-between text-xs mb-2">
                   <span class="text-gray-400 font-medium">Disk</span>
                   <span class="font-bold" :class="metrics[server.server_id].latest.disk.percent > 90 ? 'text-red-400' : 'text-amber-400'">
                     {{ metrics[server.server_id].latest.disk.percent }}%
                   </span>
                </div>
                <div class="w-full bg-gray-800 rounded-full h-1.5 overflow-hidden">
                  <div class="h-full rounded-full transition-all duration-500" 
                       :class="metrics[server.server_id].latest.disk.percent > 90 ? 'bg-red-500' : 'bg-amber-500'" 
                       :style="{ width: metrics[server.server_id].latest.disk.percent + '%' }"></div>
                </div>
              </div>
              
              <!-- Network -->
              <div v-if="visibleMetrics.network" class="bg-gray-900/30 rounded-lg p-3 border border-gray-800">
                <div class="flex justify-between items-center text-xs">
                  <div class="flex items-center gap-2">
                     <svg class="w-3 h-3 text-blue-400" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 16V4m0 0L3 8m4-4l4 4m6 0v12m0 0l4-4m-4 4l-4-4"/></svg>
                     <span class="text-gray-400">Network I/O</span>
                  </div>
                  <span v-if="metrics[server.server_id].latest.network" class="font-mono text-gray-300">
                    <span class="text-blue-400">↑</span> {{ formatBytes(metrics[server.server_id].latest.network.bytes_sent || 0) }}
                    <span class="mx-1 text-gray-700">|</span>
                    <span class="text-purple-400">↓</span> {{ formatBytes(metrics[server.server_id].latest.network.bytes_recv || 0) }}
                  </span>
                  <span v-else class="text-gray-600">-</span>
                </div>
              </div>
            </div>
            
            <!-- Footer Info -->
            <div class="px-6 py-4 border-t border-gray-800 bg-gray-900/50 flex justify-between items-center text-[10px] text-gray-500">
                <div class="flex items-center gap-3" v-if="metrics[server.server_id]">
                  <span class="flex items-center gap-1.5">
                    <svg class="w-3 h-3 text-gray-600" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" /></svg>
                    {{ metrics[server.server_id].latest.docker.running_containers }} containers
                  </span>
                  <span v-if="metrics[server.server_id].latest.uptime" class="flex items-center gap-1.5">
                    <svg class="w-3 h-3 text-gray-600" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
                    {{ formatUptime(metrics[server.server_id].latest.uptime) }}
                  </span>
                </div>
                <div v-else class="italic">Offline</div>
                
                <div class="flex gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                   <button @click.stop="exportData('csv', server.server_id)" class="text-gray-500 hover:text-white" title="Export CSV">
                     <svg class="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" /></svg>
                   </button>
                </div>
            </div>
          </div>
        </div>
      </div>
    </main>

    <!-- Install Modal -->
    <div v-if="showInstallModal" class="fixed inset-0 z-50 overflow-y-auto" aria-labelledby="modal-title" role="dialog" aria-modal="true">
      <div class="fixed inset-0 bg-black/80 backdrop-blur-sm transition-opacity" @click="showInstallModal = false"></div>

      <div class="flex min-h-full items-end justify-center p-4 text-center sm:items-center sm:p-0">
        <div class="relative transform overflow-hidden rounded-2xl bg-[#1f2937] text-left shadow-2xl border border-gray-700 transition-all sm:my-8 sm:w-full sm:max-w-lg">
          <div class="bg-[#1f2937] px-4 pt-5 pb-4 sm:p-6 sm:pb-4">
            <div class="sm:flex sm:items-start">
              <div class="mx-auto flex-shrink-0 flex items-center justify-center h-12 w-12 rounded-xl bg-indigo-900/30 text-indigo-400 sm:mx-0 sm:h-10 sm:w-10">
                <svg class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                </svg>
              </div>
              <div class="mt-3 text-center sm:mt-0 sm:ml-4 sm:text-left w-full">
                <h3 class="text-lg leading-6 font-bold text-white" id="modal-title">Install Agent</h3>
                
                <div class="flex space-x-2 mt-6 border-b border-gray-700">
                   <button 
                     @click="installOS = 'linux'"
                     :class="[installOS === 'linux' ? 'border-indigo-500 text-indigo-400' : 'border-transparent text-gray-400 hover:text-gray-300 hover:border-gray-600', 'whitespace-nowrap py-2 px-4 border-b-2 font-medium text-sm transition-colors flex items-center gap-2']"
                   >
                     <img src="../assets/linux-logo.png" class="w-5 h-5 object-contain" />
                     Linux / macOS
                   </button>
                   <button 
                     @click="installOS = 'windows'"
                     :class="[installOS === 'windows' ? 'border-indigo-500 text-indigo-400' : 'border-transparent text-gray-400 hover:text-gray-300 hover:border-gray-600', 'whitespace-nowrap py-2 px-4 border-b-2 font-medium text-sm transition-colors flex items-center gap-2']"
                   >
                     <img src="../assets/windows-logo.png" class="w-5 h-5 object-contain" />
                     Windows (PowerShell)
                   </button>
                </div>

                <div class="mt-6">
                  <p class="text-sm text-gray-400 mb-3">
                    Copy and paste this command into your {{ installOS === 'windows' ? 'PowerShell' : 'terminal' }}:
                  </p>
                  <div class="relative rounded-lg shadow-lg group">
                    <div class="bg-black text-gray-300 p-4 rounded-lg text-sm font-mono break-all border border-gray-800 pr-10">
                      {{ installCommand }}
                    </div>
                    <button @click="copyInstallCommand" class="absolute right-2 top-2 text-gray-500 hover:text-white p-1.5 rounded hover:bg-gray-800 transition-colors" title="Copy">
                       <svg class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                       </svg>
                    </button>
                  </div>
                  <p class="mt-3 text-xs text-gray-500">
                    <span v-if="installOS === 'windows'">Requires Python installed. Run in PowerShell as Administrator.</span>
                    <span v-else>Requires Python 3 installed. Run with sudo if needed.</span>
                  </p>
                </div>
              </div>
            </div>
          </div>
          <div class="bg-[#111827] px-4 py-3 sm:px-6 sm:flex sm:flex-row-reverse border-t border-gray-700">
            <button type="button" class="w-full inline-flex justify-center rounded-lg border border-transparent shadow-sm px-4 py-2 bg-indigo-600 text-base font-medium text-white hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 sm:ml-3 sm:w-auto sm:text-sm transition-colors" @click="copyInstallCommand">
              Copy Command
            </button>
            <button type="button" class="mt-3 w-full inline-flex justify-center rounded-lg border border-gray-600 shadow-sm px-4 py-2 bg-gray-800 text-base font-medium text-gray-300 hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 sm:mt-0 sm:ml-3 sm:w-auto sm:text-sm transition-colors" @click="showInstallModal = false">
              Close
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.custom-scrollbar::-webkit-scrollbar {
  width: 8px;
  height: 8px;
}

.custom-scrollbar::-webkit-scrollbar-track {
  background: #0b1120; 
}

.custom-scrollbar::-webkit-scrollbar-thumb {
  background: #1f2937; 
  border-radius: 4px;
}

.custom-scrollbar::-webkit-scrollbar-thumb:hover {
  background: #374151; 
}
</style>
