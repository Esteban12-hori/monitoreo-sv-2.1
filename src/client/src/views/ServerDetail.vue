<script setup>
import { ref, onMounted, onUnmounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import axios from 'axios'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler
} from 'chart.js'
import { Line } from 'vue-chartjs'

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler
)

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const serverId = route.params.id
const API_BASE = '' // Use relative path to leverage proxy

const timeRange = ref(1)
const chartDataCpu = ref(null)
const chartDataMem = ref(null)
const chartDataDisk = ref(null)
const chartDataNetwork = ref(null)
const latestMetrics = ref(null)
const serverInfo = ref(null)
const lastUpdate = ref('-')
const isOnline = ref(false)
const isLoading = ref(false)
const isConfigModalOpen = ref(false)
const tempInterval = ref(300)
const savingInterval = ref(false)
let pollTimer = null

const isAdmin = computed(() => authStore.isAdmin)

const isRedisRunning = computed(() => {
  if (!latestMetrics.value || !latestMetrics.value.services) return false
  const services = parseServices(latestMetrics.value.services)
  return services.some(s => s.port === 6379 || (s.name && s.name.toLowerCase().includes('redis')))
})

const servicesSummary = computed(() => {
  const list = latestMetrics.value && latestMetrics.value.services ? parseServices(latestMetrics.value.services) : []
  const criticalPorts = new Set([22, 80, 443, 3389, 5900, 8080])
  let total = 0
  let publicCount = 0
  let critical = 0
  for (const s of list) {
    if (!s) continue
    total += 1
    const ip = s.ip
    const port = Number(s.port)
    if (!ip || ip === '0.0.0.0' || ip === '::') {
      publicCount += 1
    }
    if (criticalPorts.has(port)) {
      critical += 1
    }
  }
  return { total, publicCount, critical }
})

const intervalOptions = [
  { value: 0, label: 'Desactivado (Heartbeat)' },
  { value: 5, label: 'Tiempo real (5s)' },
  { value: 60, label: '1 minuto' },
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

const openConfigModal = async () => {
  // Siempre intentar recargar la info para asegurar datos frescos
  await fetchServerInfo()

  if (serverInfo.value) {
    tempInterval.value = serverInfo.value.report_interval ?? 300
    isConfigModalOpen.value = true
  } else {
    // Si falla, intentamos usar los datos que ya tengamos o mostramos error
    alert('Información del servidor no disponible. Intente recargar la página.')
  }
}

const saveInterval = async () => {
  if (!serverInfo.value) return
  savingInterval.value = true
  try {
    await axios.put(`${API_BASE}/api/admin/servers/${serverId}/config`, {
      report_interval: parseInt(tempInterval.value)
    }, { headers: authStore.getHeaders() })
    
    serverInfo.value.report_interval = parseInt(tempInterval.value)
    alert('Intervalo actualizado correctamente.')
    isConfigModalOpen.value = false
  } catch (e) {
    console.error(e)
    alert('Error al actualizar intervalo: ' + (e.response?.data?.detail || e.message))
  } finally {
    savingInterval.value = false
  }
}

const copyServiceEndpoint = async (svc) => {
  const text = `${svc.ip || '*'}:${svc.port}/${svc.proto || 'tcp'}`
  try {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      await navigator.clipboard.writeText(text)
      alert(`Copiado: ${text}`)
    } else {
      window.prompt('Copiar endpoint del servicio:', text)
    }
  } catch (e) {
    window.prompt('Copiar endpoint del servicio:', text)
  }
}

const openServiceInfo = (svc) => {
  const name = svc.name || 'servicio'
  const query = encodeURIComponent(`${name} puerto ${svc.port} ${svc.proto || ''}`.trim())
  window.open(`https://www.google.com/search?q=${query}`, '_blank', 'noopener')
}

const chartOptions = {
  responsive: true,
  maintainAspectRatio: false,
  animation: false,
  interaction: {
    mode: 'index',
    intersect: false,
  },
  plugins: {
    legend: { display: false },
    tooltip: {
      backgroundColor: 'rgba(17, 24, 39, 0.9)',
      titleColor: '#22d3ee',
      bodyColor: '#e5e7eb',
      borderColor: 'rgba(34, 211, 238, 0.2)',
      borderWidth: 1,
      padding: 10,
      cornerRadius: 8,
      displayColors: false,
      callbacks: {
        label: (context) => ` ${context.dataset.label}: ${context.parsed.y.toFixed(1)}%`
      }
    }
  },
  scales: {
    y: {
      beginAtZero: true,
      max: 100,
      grid: { 
        color: 'rgba(156, 163, 175, 0.1)',
        drawBorder: false 
      },
      ticks: { 
        color: '#94a3b8', 
        font: { size: 10, family: "'Inter', sans-serif" }
      },
      border: { display: false }
    },
    x: {
      grid: { display: false },
      ticks: { display: false }, // Hide x labels for cleaner look
      border: { display: false }
    }
  },
  elements: {
    line: {
      tension: 0.4,
      borderWidth: 2
    },
    point: {
      radius: 0,
      hitRadius: 10,
      hoverRadius: 4
    }
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
  const d = Math.floor(seconds / (3600*24));
  const h = Math.floor(seconds % (3600*24) / 3600);
  const m = Math.floor(seconds % 3600 / 60);
  let s = '';
  if (d > 0) s += `${d}d `;
  if (h > 0) s += `${h}h `;
  s += `${m}m`;
  return s || '0m';
}

const parseDocker = (jsonStr) => {
  if (!jsonStr) return []
  if (Array.isArray(jsonStr)) return jsonStr
  try {
    return JSON.parse(jsonStr)
  } catch (e) {
    return []
  }
}

const parseServices = (val) => {
  if (!val) return []
  if (Array.isArray(val)) return val
  try {
    return JSON.parse(val)
  } catch (e) {
    return []
  }
}

const parseProcesses = (val) => {
  if (!val) return []
  if (Array.isArray(val)) return val
  try {
    return JSON.parse(val)
  } catch (e) {
    return []
  }
}

const getPortBadgeClasses = (port) => {
  const p = Number(port)
  if ([22, 80, 443, 3389, 5900, 8080].includes(p)) {
    return 'bg-red-500/10 text-red-400 border-red-500/20'
  }
  return 'bg-gray-700/50 text-gray-300 border-gray-600'
}

const getProtoBadgeClasses = (proto) => {
  const p = (proto || 'tcp').toString().toLowerCase()
  if (p === 'udp') {
    return 'bg-sky-500/10 text-sky-400 border-sky-500/20'
  }
  return 'bg-blue-500/10 text-blue-400 border-blue-500/20'
}

const getCardBorderClass = (val, warning = 75, critical = 90) => {
  if (val >= critical) return 'border-red-500/50 shadow-[0_0_15px_rgba(239,68,68,0.2)]'
  if (val >= warning) return 'border-amber-500/50 shadow-[0_0_15px_rgba(245,158,11,0.2)]'
  return 'border-gray-700 hover:border-cyan-500/30'
}

const getIpBadgeClasses = (ip) => {
  if (!ip || ip === '0.0.0.0' || ip === '::') {
    return 'bg-amber-500/10 text-amber-400 border-amber-500/20'
  }
  return 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
}

const fetchServerInfo = async () => {
  try {
    const res = await axios.get(`${API_BASE}/api/servers`, { headers: authStore.getHeaders() })
    serverInfo.value = res.data.find(s => s.server_id === serverId)
  } catch (e) {
    console.error(e)
    if (e.response && e.response.status === 401) {
       authStore.logout()
       router.push('/login')
    }
  }
}

const fetchHistory = async () => {
  if (!latestMetrics.value) isLoading.value = true
  try {
    const limit = 2000 
    const res = await axios.get(`${API_BASE}/api/metrics/history`, {
      params: {
        server_id: serverId,
        hours: timeRange.value,
        limit: limit
      },
      headers: authStore.getHeaders()
    })

    const data = res.data
    if (data.length > 0) {
      const last = data[data.length - 1]
      latestMetrics.value = last
      
      if (last.network && (last.network.sent_rate !== undefined || last.network.recv_rate !== undefined)) {
          latestMetrics.value.net_sent_rate = last.network.sent_rate || 0
          latestMetrics.value.net_recv_rate = last.network.recv_rate || 0
      } else if (data.length >= 2) {
         const prev = data[data.length - 2]
         const timeDiff = (new Date(last.ts) - new Date(prev.ts)) / 1000
         if (timeDiff > 0 && last.network && prev.network) {
            latestMetrics.value.net_sent_rate = (last.network.bytes_sent - prev.network.bytes_sent) / timeDiff
            latestMetrics.value.net_recv_rate = (last.network.bytes_recv - prev.network.bytes_recv) / timeDiff
         }
      }

      lastUpdate.value = new Date(last.ts).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
      
      const lastTs = new Date(last.ts).getTime()
      const now = new Date().getTime()
      const diffMinutes = (now - lastTs) / 1000 / 60
      const tolerance = (last.report_interval ? (last.report_interval * 2 / 60) : 5) 
      isOnline.value = diffMinutes < tolerance
      
      const labels = data.map(d => new Date(d.ts).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }))
      
      const gradient = (ctx, color1, color2) => {
        const g = ctx.createLinearGradient(0, 0, 0, 200)
        g.addColorStop(0, color1)
        g.addColorStop(1, color2)
        return g
      }
      
      chartDataCpu.value = {
        labels,
        datasets: [{
          label: 'CPU',
          data: data.map(d => d.cpu.total),
          borderColor: '#22d3ee', // cyan-400
          backgroundColor: (context) => {
            const ctx = context.chart.ctx;
            return gradient(ctx, 'rgba(34, 211, 238, 0.2)', 'rgba(34, 211, 238, 0.0)')
          },
          fill: true,
          tension: 0.4,
          pointRadius: 0
        }]
      }
      
      chartDataMem.value = {
        labels,
        datasets: [{
          label: 'Memoria',
          data: data.map(d => (d.memory.used / d.memory.total * 100)),
          borderColor: '#34d399', // emerald-400
          backgroundColor: (context) => {
            const ctx = context.chart.ctx;
            return gradient(ctx, 'rgba(52, 211, 153, 0.2)', 'rgba(52, 211, 153, 0.0)')
          },
          fill: true,
          tension: 0.4,
          pointRadius: 0
        }]
      }
      
    } else {
      latestMetrics.value = null
    }

  } catch (error) {
    console.error("Error fetching metrics detail", error)
    if (error.response && error.response.status === 401) {
       authStore.logout()
       router.push('/login')
    }
  } finally {
    isLoading.value = false
  }
}

onMounted(async () => {
  await fetchServerInfo()
  await fetchHistory()
  pollTimer = setInterval(fetchHistory, 10000)
})

onUnmounted(() => {
  if (pollTimer) clearInterval(pollTimer)
})
</script>

<template>
  <div class="min-h-screen bg-[#0b1120] text-gray-100 font-sans selection:bg-cyan-500/30">
    
    <!-- Top Navigation -->
    <header class="bg-[#111827]/80 backdrop-blur-md border-b border-gray-800 sticky top-0 z-30">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex justify-between items-center">
        <div class="flex items-center gap-4">
          <button 
            @click="router.back()" 
            class="p-2 rounded-lg hover:bg-gray-800 text-gray-400 hover:text-white transition-colors"
          >
            <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 19l-7-7m0 0l7-7m-7 7h18" />
            </svg>
          </button>
          <h1 class="text-xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-cyan-400 to-emerald-400">
            {{ serverId }}
          </h1>
          <span v-if="serverInfo?.group_name" class="px-2 py-0.5 rounded-full text-xs bg-gray-800 text-gray-300 border border-gray-700">
            {{ serverInfo.group_name }}
          </span>
        </div>
        
        <div class="flex items-center gap-3">
          <div class="hidden sm:flex items-center gap-2 text-xs text-gray-500 mr-4">
            <span class="flex items-center gap-1.5">
              <span class="w-2 h-2 rounded-full" :class="isOnline ? 'bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.5)]' : 'bg-red-500'"></span>
              {{ isOnline ? 'ONLINE' : 'OFFLINE' }}
            </span>
            <span class="text-gray-700">|</span>
            <span>Last update: {{ lastUpdate }}</span>
          </div>

          <button 
            @click="openConfigModal"
            class="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-gray-800 border border-gray-700 text-sm font-medium hover:bg-gray-700 hover:border-gray-600 transition-all"
          >
            <svg class="w-4 h-4 text-cyan-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
            </svg>
            Config
          </button>
        </div>
      </div>
    </header>

    <main class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      
      <!-- Loading State -->
      <div v-if="isLoading && !latestMetrics" class="flex justify-center items-center h-64">
        <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-cyan-500"></div>
      </div>

      <!-- Content Grid -->
      <div v-else-if="latestMetrics" class="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        <!-- Left Column: Charts -->
        <div class="lg:col-span-2 space-y-6">
          
          <!-- CPU Chart -->
          <div class="bg-[#111827] rounded-2xl p-6 border border-gray-800 shadow-xl relative overflow-hidden group">
            <div class="relative z-10">
              <h3 class="text-lg font-semibold text-gray-100 flex items-center gap-2 mb-4">
                <span class="w-1 h-6 bg-cyan-500 rounded-full shadow-[0_0_10px_rgba(6,182,212,0.5)]"></span>
                CPU Usage
                <span class="text-xs font-normal text-gray-500 ml-auto">Real time</span>
              </h3>
              <div class="h-64">
                <Line v-if="chartDataCpu" :data="chartDataCpu" :options="chartOptions" />
              </div>
            </div>
          </div>

          <!-- RAM Chart -->
          <div class="bg-[#111827] rounded-2xl p-6 border border-gray-800 shadow-xl relative overflow-hidden group">
            <div class="relative z-10">
              <h3 class="text-lg font-semibold text-gray-100 flex items-center gap-2 mb-4">
                <span class="w-1 h-6 bg-emerald-500 rounded-full shadow-[0_0_10px_rgba(16,185,129,0.5)]"></span>
                RAM Usage
                <span class="text-xs font-normal text-gray-500 ml-auto">Real time</span>
              </h3>
              <div class="h-64">
                <Line v-if="chartDataMem" :data="chartDataMem" :options="chartOptions" />
              </div>
            </div>
          </div>

          <!-- Docker Containers List -->
          <div class="bg-[#111827] rounded-2xl border border-gray-800 shadow-xl overflow-hidden">
            <div class="px-6 py-4 border-b border-gray-800 flex justify-between items-center bg-gray-900/50">
               <h3 class="text-sm font-semibold text-gray-300 uppercase tracking-wider">Docker Containers</h3>
               <span class="bg-gray-800 text-gray-400 px-2 py-0.5 rounded text-xs">{{ parseDocker(latestMetrics.docker.containers).length }}</span>
            </div>
            <div class="overflow-x-auto">
              <table class="w-full text-left text-sm text-gray-400">
                <thead class="bg-gray-800/50 text-xs uppercase text-gray-500">
                  <tr>
                    <th class="px-6 py-3">Name</th>
                    <th class="px-6 py-3">Image</th>
                    <th class="px-6 py-3">Status</th>
                  </tr>
                </thead>
                <tbody class="divide-y divide-gray-800">
                  <tr v-for="(c, i) in parseDocker(latestMetrics.docker.containers)" :key="i" class="hover:bg-gray-800/30 transition-colors">
                    <td class="px-6 py-3 font-medium text-gray-200">{{ c.name }}</td>
                    <td class="px-6 py-3 text-xs">{{ c.image }}</td>
                    <td class="px-6 py-3">
                      <span class="text-emerald-400 text-xs bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20">Running</span>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>

        </div>

        <!-- Right Column: KPI Cards -->
        <div class="space-y-4">
          
          <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-1 xl:grid-cols-2 gap-4">
            
            <!-- Server CPU KPI -->
            <div class="bg-[#111827] p-5 rounded-2xl border border-gray-800 relative overflow-hidden group hover:border-cyan-500/30 transition-all">
               <div class="relative z-10">
                 <div class="text-cyan-400 text-xs font-bold uppercase tracking-wider mb-2">Server CPU</div>
                 <div class="flex items-end gap-2">
                   <span class="text-4xl font-bold text-white">{{ latestMetrics.cpu.total.toFixed(1) }}%</span>
                 </div>
                 <div class="mt-3 flex items-center gap-2 text-xs text-gray-400">
                   <span class="w-2 h-2 rounded-full bg-cyan-500 animate-pulse"></span>
                   {{ (latestMetrics.cpu.per_core || []).length }} Cores Active
                 </div>
               </div>
            </div>

            <!-- Memory KPI -->
            <div class="bg-[#111827] p-5 rounded-2xl border border-gray-800 relative overflow-hidden group hover:border-emerald-500/30 transition-all">
               <div class="relative z-10">
                 <div class="text-emerald-400 text-xs font-bold uppercase tracking-wider mb-2">Realtime Monitoring</div>
                 <div class="flex items-end gap-2">
                   <span class="text-4xl font-bold text-white">{{ ((latestMetrics.memory.used / latestMetrics.memory.total) * 100).toFixed(0) }}%</span>
                 </div>
                 <div class="mt-3 flex items-center gap-2 text-xs text-emerald-400 bg-emerald-500/10 px-2 py-1 rounded w-fit">
                   <svg class="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/></svg>
                   {{ formatBytes(latestMetrics.memory.used) }} Used
                 </div>
               </div>
            </div>

            <!-- Disk Space KPI -->
            <div class="bg-[#111827] p-5 rounded-2xl border border-gray-800 relative overflow-hidden group hover:border-purple-500/30 transition-all">
               <div class="relative z-10">
                 <div class="text-purple-400 text-xs font-bold uppercase tracking-wider mb-2">Disk Space</div>
                 <div class="flex items-end gap-2">
                   <span class="text-4xl font-bold text-white">{{ latestMetrics.disk.percent.toFixed(0) }}%</span>
                 </div>
                 <div class="mt-3 w-full bg-gray-800 rounded-full h-1.5">
                    <div class="bg-purple-500 h-1.5 rounded-full" :style="{ width: latestMetrics.disk.percent + '%' }"></div>
                 </div>
                 <div class="mt-2 text-xs text-gray-400 text-right">
                    {{ formatBytes(latestMetrics.disk.free) }} Free
                 </div>
               </div>
            </div>

            <!-- Network KPI -->
            <div class="bg-[#111827] p-5 rounded-2xl border border-gray-800 relative overflow-hidden group hover:border-indigo-500/30 transition-all">
               <div class="relative z-10">
                 <div class="text-indigo-400 text-xs font-bold uppercase tracking-wider mb-2">Network Traffic</div>
                 <div class="flex flex-col gap-1">
                   <div class="flex justify-between items-center">
                      <span class="text-xs text-gray-500">UP</span>
                      <span class="text-lg font-bold text-white">{{ formatBytes(latestMetrics.net_sent_rate || 0) }}/s</span>
                   </div>
                   <div class="flex justify-between items-center">
                      <span class="text-xs text-gray-500">DOWN</span>
                      <span class="text-lg font-bold text-white">{{ formatBytes(latestMetrics.net_recv_rate || 0) }}/s</span>
                   </div>
                 </div>
               </div>
            </div>

            <!-- Redis Status -->
            <div class="bg-[#111827] p-5 rounded-2xl border border-gray-800 relative overflow-hidden group hover:border-red-500/30 transition-all">
               <div class="relative z-10">
                 <div class="text-red-400 text-xs font-bold uppercase tracking-wider mb-2">Redis Service</div>
                 <div class="flex items-center gap-3">
                   <div class="text-2xl font-bold text-white">{{ isRedisRunning ? 'Active' : 'Stopped' }}</div>
                   <span v-if="isRedisRunning" class="flex h-3 w-3 relative">
                      <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75"></span>
                      <span class="relative inline-flex rounded-full h-3 w-3 bg-red-500"></span>
                   </span>
                 </div>
                 <div class="mt-3 text-xs text-gray-500">
                    Port 6379 Monitoring
                 </div>
               </div>
            </div>
             
             <!-- Server Status -->
            <div class="bg-[#111827] p-5 rounded-2xl border border-gray-800 relative overflow-hidden group hover:border-green-500/30 transition-all">
               <div class="relative z-10">
                 <div class="text-green-400 text-xs font-bold uppercase tracking-wider mb-2">System Uptime</div>
                 <div class="text-xl font-bold text-white">{{ formatUptime(latestMetrics.uptime) }}</div>
                 <div class="mt-3 text-xs text-gray-500">
                    Since last reboot
                 </div>
               </div>
            </div>

          </div>
          
          <!-- Services List Mini -->
          <div class="bg-[#111827] rounded-2xl border border-gray-800 p-4">
             <h3 class="text-xs font-bold text-gray-400 uppercase tracking-wider mb-3 flex justify-between items-center">
               Detected Services
               <span class="bg-gray-800 text-gray-300 px-1.5 py-0.5 rounded text-[10px]">{{ servicesSummary.total }}</span>
             </h3>
             <div class="space-y-2 max-h-60 overflow-y-auto pr-2 custom-scrollbar">
                <div v-for="(svc, i) in parseServices(latestMetrics.services).slice(0, 10)" :key="i" class="flex items-center justify-between p-2 rounded bg-gray-800/40 hover:bg-gray-800/80 transition-colors">
                   <div class="flex items-center gap-2">
                      <div class="w-1.5 h-1.5 rounded-full" :class="svc.ip === '0.0.0.0' ? 'bg-amber-500' : 'bg-emerald-500'"></div>
                      <span class="text-sm text-gray-300 font-medium">{{ svc.name }}</span>
                   </div>
                   <span class="text-xs text-gray-500 font-mono">{{ svc.port }}</span>
                </div>
             </div>
          </div>

        </div>

      </div>
      
      <!-- Empty State -->
      <div v-else class="text-center py-20">
         <div class="inline-flex bg-gray-800 p-4 rounded-full mb-4">
            <svg class="w-8 h-8 text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
         </div>
         <h2 class="text-xl font-semibold text-white">No Metrics Available</h2>
         <p class="text-gray-400 mt-2">Waiting for server {{ serverId }} to report data...</p>
      </div>

    </main>

    <!-- Config Modal -->
    <div v-if="isConfigModalOpen" class="fixed inset-0 z-[100] overflow-y-auto" aria-labelledby="modal-title" role="dialog" aria-modal="true">
      <div class="flex items-center justify-center min-h-screen px-4 text-center sm:block sm:p-0">
        <div class="fixed inset-0 bg-black/80 transition-opacity backdrop-blur-sm" aria-hidden="true" @click="isConfigModalOpen = false"></div>
        <span class="hidden sm:inline-block sm:align-middle sm:h-screen" aria-hidden="true">&#8203;</span>
        <div class="inline-block align-bottom bg-[#1f2937] rounded-2xl text-left overflow-hidden shadow-2xl transform transition-all sm:my-8 sm:align-middle sm:max-w-lg w-full border border-gray-700 relative z-10">
          <div class="px-6 py-6">
             <h3 class="text-lg font-bold text-white mb-4 flex items-center gap-2">
               <svg class="w-5 h-5 text-cyan-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                 <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                 <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
               </svg>
               Server Configuration
             </h3>
             <div class="space-y-4">
               <div>
                 <label class="block text-sm font-medium text-gray-300 mb-2">Update Interval</label>
                 <select v-model="tempInterval" class="w-full bg-gray-900 border border-gray-600 text-white rounded-lg px-4 py-2.5 focus:ring-2 focus:ring-cyan-500 focus:border-transparent outline-none transition-all">
                    <option v-for="opt in intervalOptions" :key="opt.value" :value="opt.value">{{ opt.label }}</option>
                 </select>
                 <p class="mt-2 text-xs text-gray-400">Controls how often the agent sends metrics to the server.</p>
               </div>
             </div>
          </div>
          <div class="bg-gray-900/50 px-6 py-4 flex justify-end gap-3 border-t border-gray-700">
             <button @click="isConfigModalOpen = false" class="px-4 py-2 rounded-lg text-gray-300 hover:text-white hover:bg-gray-800 transition-colors text-sm font-medium border border-gray-600 hover:border-gray-500">Cancel</button>
             <button 
               @click="saveInterval" 
               :disabled="savingInterval"
               class="px-4 py-2 rounded-lg bg-gradient-to-r from-cyan-600 to-blue-600 text-white hover:from-cyan-500 hover:to-blue-500 transition-all text-sm font-medium flex items-center gap-2 disabled:opacity-50 shadow-lg shadow-cyan-500/20"
             >
               <svg v-if="savingInterval" class="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg>
               {{ savingInterval ? 'Saving...' : 'Save Changes' }}
             </button>
          </div>
        </div>
      </div>
    </div>

  </div>
</template>

<style scoped>
/* Custom Scrollbar */
.custom-scrollbar::-webkit-scrollbar {
  width: 4px;
}
.custom-scrollbar::-webkit-scrollbar-track {
  background: rgba(31, 41, 55, 0.5);
}
.custom-scrollbar::-webkit-scrollbar-thumb {
  background: rgba(75, 85, 99, 0.5);
  border-radius: 2px;
}
.custom-scrollbar::-webkit-scrollbar-thumb:hover {
  background: rgba(107, 114, 128, 0.8);
}
</style>
