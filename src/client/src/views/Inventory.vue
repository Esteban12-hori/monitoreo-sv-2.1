<script setup>
import { ref, onMounted, computed } from 'vue'
import axios from 'axios'
import { useAuthStore } from '../stores/auth'
import { useRouter } from 'vue-router'

const authStore = useAuthStore()
const router = useRouter()
const H = () => ({ headers: authStore.getHeaders() })

const message = ref('')
const error = ref('')
const notify = (msg, isError = false) => {
  if (isError) { error.value = msg; message.value = '' }
  else { message.value = msg; error.value = '' }
  setTimeout(() => { message.value = ''; error.value = '' }, 5000)
}
const handleErr = (e) => {
  if (e.response && e.response.status === 401) { authStore.logout(); router.push('/login'); return }
  notify(e.response?.data?.detail || e.message, true)
}

// --- Inventario unificado ---
const items = ref([])
const filter = ref('all')
const loading = ref(false)
const loadInventory = async () => {
  loading.value = true
  try { items.value = (await axios.get('/api/inventory', H())).data } catch (e) { handleErr(e) }
  finally { loading.value = false }
}
const filtered = computed(() =>
  filter.value === 'all' ? items.value : items.value.filter(i => i.source === filter.value)
)
const counts = computed(() => ({
  all: items.value.length,
  agent: items.value.filter(i => i.source === 'agent').length,
  agentless: items.value.filter(i => i.source === 'agentless').length,
  proxmox: items.value.filter(i => i.source === 'proxmox').length,
}))
const sourceLabel = { agent: 'Agente', agentless: 'Agentless', proxmox: 'Proxmox' }
const statusClass = (s) => {
  if (['online', 'up', 'running'].includes(s)) return 'bg-green-800'
  if (['offline', 'down', 'stopped'].includes(s)) return 'bg-red-800'
  return 'bg-gray-700'
}

// --- Auto-descubrimiento de red ---
const scan = ref({ cidr: '', ports: '', timeout: 0.5, use_icmp: true, auto_create: false })
const scanning = ref(false)
const discovered = ref(null)
const runScan = async () => {
  scanning.value = true
  discovered.value = null
  try {
    const payload = {
      cidr: scan.value.cidr,
      timeout: scan.value.timeout,
      use_icmp: scan.value.use_icmp,
      auto_create: scan.value.auto_create,
    }
    const ports = scan.value.ports.split(',').map(p => parseInt(p.trim())).filter(p => p)
    if (ports.length) payload.ports = ports
    const r = await axios.post('/api/discovery/scan', payload, H())
    discovered.value = r.data
    notify(`Descubiertos ${r.data.found} host(s)` + (r.data.created_checks ? `, ${r.data.created_checks} check(s) creados` : ''))
    if (r.data.created_checks) await loadInventory()
  } catch (e) { handleErr(e) } finally { scanning.value = false }
}

onMounted(loadInventory)
</script>

<template>
  <div class="min-h-screen bg-[#0b0f17] text-gray-100 p-6">
    <div class="max-w-6xl mx-auto">
      <div class="flex items-center justify-between mb-6">
        <div>
          <h1 class="text-2xl font-bold">Inventario unificado</h1>
          <p class="text-gray-500 text-sm">Agentes, checks agentless y guests Proxmox en una sola vista.</p>
        </div>
        <router-link to="/dashboard" class="text-cyan-400 hover:text-cyan-300 text-sm">← Dashboard</router-link>
      </div>

      <div v-if="message" class="mb-4 px-4 py-2 bg-green-900/40 border border-green-700 rounded text-sm">{{ message }}</div>
      <div v-if="error" class="mb-4 px-4 py-2 bg-red-900/40 border border-red-700 rounded text-sm">{{ error }}</div>

      <!-- Descubrimiento de red -->
      <div class="bg-[#111827] border border-gray-800 rounded-xl p-4 mb-6">
        <h2 class="font-semibold mb-3">Auto-descubrimiento de red</h2>
        <div class="grid grid-cols-1 md:grid-cols-5 gap-2 items-end">
          <div><label class="text-xs text-gray-400">CIDR</label><input v-model="scan.cidr" placeholder="192.168.1.0/24" class="w-full px-2 py-1 bg-gray-800 rounded border border-gray-700 text-sm" /></div>
          <div><label class="text-xs text-gray-400">Puertos (coma)</label><input v-model="scan.ports" placeholder="22,80,443" class="w-full px-2 py-1 bg-gray-800 rounded border border-gray-700 text-sm" /></div>
          <div><label class="text-xs text-gray-400">Timeout (s)</label><input v-model.number="scan.timeout" type="number" step="0.1" class="w-full px-2 py-1 bg-gray-800 rounded border border-gray-700 text-sm" /></div>
          <label class="flex items-center gap-1 text-xs text-gray-400"><input type="checkbox" v-model="scan.use_icmp" /> ICMP fallback</label>
          <label class="flex items-center gap-1 text-xs text-gray-400"><input type="checkbox" v-model="scan.auto_create" /> Crear checks</label>
        </div>
        <button @click="runScan" :disabled="scanning || !scan.cidr" class="mt-3 px-4 py-2 bg-cyan-600 hover:bg-cyan-700 disabled:opacity-50 rounded text-sm">
          {{ scanning ? 'Escaneando…' : 'Escanear red' }}
        </button>
        <div v-if="discovered" class="mt-3 text-sm">
          <p class="text-gray-400 mb-1">{{ discovered.found }} host(s) vivo(s):</p>
          <ul class="space-y-1">
            <li v-for="h in discovered.hosts" :key="h.host" class="font-mono text-xs">
              {{ h.host }} <span class="text-gray-500">({{ h.method }}{{ h.open_ports.length ? ': ' + h.open_ports.join(',') : '' }})</span>
            </li>
            <li v-if="discovered.hosts.length === 0" class="text-gray-500 text-xs">Ninguno.</li>
          </ul>
        </div>
      </div>

      <!-- Filtros -->
      <div class="flex flex-wrap gap-2 mb-3">
        <button v-for="f in ['all','agent','agentless','proxmox']" :key="f" @click="filter = f"
          class="px-3 py-1 rounded text-xs" :class="filter === f ? 'bg-cyan-700' : 'bg-gray-800'">
          {{ f === 'all' ? 'Todos' : sourceLabel[f] }} ({{ counts[f] }})
        </button>
        <button @click="loadInventory" class="ml-auto px-3 py-1 bg-gray-700 rounded text-xs">Refrescar</button>
      </div>

      <!-- Tabla -->
      <div class="bg-[#111827] border border-gray-800 rounded-xl overflow-hidden">
        <table class="w-full text-sm">
          <thead class="bg-gray-900/60 text-gray-400 text-xs">
            <tr>
              <th class="text-left px-3 py-2">Origen</th>
              <th class="text-left px-3 py-2">Nombre</th>
              <th class="text-left px-3 py-2">Identificador</th>
              <th class="text-left px-3 py-2">Tipo</th>
              <th class="text-left px-3 py-2">Estado</th>
              <th class="text-left px-3 py-2">Detalle</th>
              <th class="text-left px-3 py-2">Nodo</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(i, idx) in filtered" :key="idx" class="border-t border-gray-800">
              <td class="px-3 py-2"><span class="text-xs px-2 py-0.5 rounded bg-gray-700">{{ sourceLabel[i.source] }}</span></td>
              <td class="px-3 py-2">{{ i.name }}</td>
              <td class="px-3 py-2 font-mono text-xs text-gray-400">{{ i.identifier }}</td>
              <td class="px-3 py-2 text-gray-400">{{ i.kind }}</td>
              <td class="px-3 py-2"><span v-if="i.status" class="text-xs px-2 py-0.5 rounded" :class="statusClass(i.status)">{{ i.status }}</span></td>
              <td class="px-3 py-2 text-gray-400 text-xs">{{ i.detail }}</td>
              <td class="px-3 py-2 text-gray-400 text-xs">{{ i.node }}</td>
            </tr>
            <tr v-if="!loading && filtered.length === 0"><td colspan="7" class="px-3 py-6 text-center text-gray-500">Sin elementos.</td></tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>
