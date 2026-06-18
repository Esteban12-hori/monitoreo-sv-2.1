<script setup>
import { ref, onMounted, computed } from 'vue'
import axios from 'axios'
import { useAuthStore } from '../stores/auth'
import { useRouter } from 'vue-router'

const authStore = useAuthStore()
const router = useRouter()
const H = () => ({ headers: authStore.getHeaders() })

const tab = ref('nodes')
const tabs = [
  { id: 'nodes', label: 'Nodos' },
  { id: 'guests', label: 'Guests' },
  { id: 'backups', label: 'Backups' },
  { id: 'migration', label: 'Migración' },
]

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

// --- Nodos ---
const nodes = ref([])
const newNode = ref({ name: '', hostname: '', ssh_port: 22, ssh_user: 'root', auth_type: 'password', secret: '', use_sudo: false })

const loadNodes = async () => {
  try { nodes.value = (await axios.get('/api/proxmox/nodes', H())).data } catch (e) { handleErr(e) }
}
const createNode = async () => {
  try {
    await axios.post('/api/proxmox/nodes', newNode.value, H())
    notify('Nodo registrado')
    newNode.value = { name: '', hostname: '', ssh_port: 22, ssh_user: 'root', auth_type: 'password', secret: '', use_sudo: false }
    await loadNodes()
  } catch (e) { handleErr(e) }
}
const testNode = async (n) => {
  try { const r = await axios.post(`/api/proxmox/nodes/${n.id}/test`, {}, H()); notify(`OK: ${r.data.version}`) } catch (e) { handleErr(e) }
}
const syncNode = async (n) => {
  try { const r = await axios.post(`/api/proxmox/nodes/${n.id}/sync`, {}, H()); notify(`Sincronizados ${r.data.count} guests`) } catch (e) { handleErr(e) }
}
const deleteNode = async (n) => {
  if (!confirm(`¿Eliminar el nodo ${n.name}?`)) return
  try { await axios.delete(`/api/proxmox/nodes/${n.id}`, H()); await loadNodes() } catch (e) { handleErr(e) }
}

// --- Guests ---
const selectedNode = ref(null)
const guests = ref([])
const loadGuests = async () => {
  if (!selectedNode.value) return
  try { guests.value = (await axios.get(`/api/proxmox/nodes/${selectedNode.value}/guests`, H())).data } catch (e) { handleErr(e) }
}
const res = ref({})  // guest_id -> {cores, memory}
const saveResources = async (g) => {
  const r = res.value[g.id] || {}
  try { await axios.put(`/api/proxmox/guests/${g.id}/resources`, { cores: r.cores || null, memory: r.memory || null }, H()); notify(`Recursos de ${g.vmid} actualizados`) } catch (e) { handleErr(e) }
}
const linkServer = async (g) => {
  try { await axios.put(`/api/proxmox/guests/${g.id}/link`, { linked_server_id: g.linked_server_id || null }, H()); notify('Vínculo actualizado'); await loadGuests() } catch (e) { handleErr(e) }
}

// Snapshots
const snaps = ref({})  // guest_id -> [snapshots]
const newSnap = ref({})
const loadSnaps = async (g) => {
  try { snaps.value = { ...snaps.value, [g.id]: (await axios.get(`/api/proxmox/guests/${g.id}/snapshots`, H())).data } } catch (e) { handleErr(e) }
}
const createSnap = async (g) => {
  try { await axios.post(`/api/proxmox/guests/${g.id}/snapshots`, { name: newSnap.value[g.id] }, H()); newSnap.value[g.id] = ''; notify('Snapshot creado'); await loadSnaps(g) } catch (e) { handleErr(e) }
}
const rollbackSnap = async (g, name) => {
  if (!confirm(`¿Restaurar al snapshot ${name}?`)) return
  try { await axios.post(`/api/proxmox/guests/${g.id}/snapshots/${name}/rollback`, {}, H()); notify('Restaurado') } catch (e) { handleErr(e) }
}
const deleteSnap = async (g, name) => {
  try { await axios.delete(`/api/proxmox/guests/${g.id}/snapshots/${name}`, H()); await loadSnaps(g) } catch (e) { handleErr(e) }
}

// --- Backups ---
const schedules = ref([])
const jobs = ref([])
const newSched = ref({ name: '', node_id: null, cron_expr: '0 3 * * *', storage: 'local', mode: 'snapshot', only_db: true, enabled: true })
const manualRun = ref({ node_id: null, vmid: null, storage: 'local', mode: 'snapshot' })
const loadBackups = async () => {
  try {
    schedules.value = (await axios.get('/api/proxmox/backup-schedules', H())).data
    jobs.value = (await axios.get('/api/proxmox/backup-jobs', H())).data
  } catch (e) { handleErr(e) }
}
const createSchedule = async () => {
  try { await axios.post('/api/proxmox/backup-schedules', newSched.value, H()); notify('Programación creada'); await loadBackups() } catch (e) { handleErr(e) }
}
const deleteSchedule = async (s) => {
  try { await axios.delete(`/api/proxmox/backup-schedules/${s.id}`, H()); await loadBackups() } catch (e) { handleErr(e) }
}
const runBackup = async () => {
  try { await axios.post('/api/proxmox/backups/run', manualRun.value, H()); notify('Backup lanzado'); await loadBackups() } catch (e) { handleErr(e) }
}

// --- Migración ---
const links = ref([])
const newLink = ref({ source_node_id: null, target_node_id: null })
const migration = ref({ link_id: null, vmid: null, guest_type: 'qemu', storage: 'local', online: false })
const loadLinks = async () => {
  try { links.value = (await axios.get('/api/proxmox/links', H())).data } catch (e) { handleErr(e) }
}
const createLink = async () => {
  try { await axios.post('/api/proxmox/links', newLink.value, H()); notify('Túnel WireGuard establecido'); await loadLinks() } catch (e) { handleErr(e) }
}
const deleteLink = async (l) => {
  if (!confirm('¿Eliminar el túnel?')) return
  try { await axios.delete(`/api/proxmox/links/${l.id}`, H()); await loadLinks() } catch (e) { handleErr(e) }
}
const migrate = async () => {
  if (!confirm('¿Migrar la carga de trabajo por el túnel cifrado?')) return
  try { await axios.post('/api/proxmox/migrate', migration.value, H()); notify('Migración completada') } catch (e) { handleErr(e) }
}

const nodeName = (id) => nodes.value.find(n => n.id === id)?.name || id

onMounted(async () => {
  await loadNodes()
  await loadBackups()
  await loadLinks()
})
</script>

<template>
  <div class="min-h-screen bg-[#0b1120] text-gray-200 py-10 px-4 sm:px-8">
    <div class="max-w-6xl mx-auto space-y-6">
      <div class="flex items-center justify-between">
        <h1 class="text-2xl font-bold text-white">Gestión Proxmox</h1>
        <router-link to="/dashboard" class="text-cyan-400 hover:text-cyan-300 text-sm">← Dashboard</router-link>
      </div>

      <div v-if="message" class="bg-green-900/30 border border-green-700 text-green-300 px-4 py-2 rounded-lg text-sm">{{ message }}</div>
      <div v-if="error" class="bg-red-900/30 border border-red-700 text-red-300 px-4 py-2 rounded-lg text-sm">{{ error }}</div>

      <!-- Tabs -->
      <div class="flex gap-2 border-b border-gray-700">
        <button v-for="t in tabs" :key="t.id" @click="tab = t.id"
          :class="['px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors',
                   tab === t.id ? 'border-cyan-400 text-cyan-400' : 'border-transparent text-gray-400 hover:text-gray-200']">
          {{ t.label }}
        </button>
      </div>

      <!-- NODOS -->
      <div v-show="tab === 'nodes'" class="space-y-6">
        <div class="bg-[#111827] border border-gray-800 rounded-xl p-5">
          <h2 class="font-semibold mb-3">Registrar nodo Proxmox</h2>
          <div class="grid grid-cols-1 md:grid-cols-3 gap-3">
            <input v-model="newNode.name" placeholder="Nombre" class="px-3 py-2 bg-gray-800 rounded border border-gray-700 text-sm" />
            <input v-model="newNode.hostname" placeholder="Host / IP (SSH)" class="px-3 py-2 bg-gray-800 rounded border border-gray-700 text-sm" />
            <input v-model.number="newNode.ssh_port" type="number" placeholder="Puerto SSH" class="px-3 py-2 bg-gray-800 rounded border border-gray-700 text-sm" />
            <input v-model="newNode.ssh_user" placeholder="Usuario SSH" class="px-3 py-2 bg-gray-800 rounded border border-gray-700 text-sm" />
            <select v-model="newNode.auth_type" class="px-3 py-2 bg-gray-800 rounded border border-gray-700 text-sm">
              <option value="password">Contraseña</option>
              <option value="key">Clave privada</option>
            </select>
            <label class="flex items-center gap-2 text-sm"><input type="checkbox" v-model="newNode.use_sudo" /> Usar sudo</label>
            <textarea v-model="newNode.secret" :placeholder="newNode.auth_type === 'key' ? 'Clave privada SSH' : 'Contraseña SSH'" class="px-3 py-2 bg-gray-800 rounded border border-gray-700 text-sm md:col-span-3" rows="2"></textarea>
          </div>
          <button @click="createNode" class="mt-3 px-4 py-2 bg-cyan-600 hover:bg-cyan-700 rounded text-sm font-medium">Registrar</button>
        </div>

        <div class="bg-[#111827] border border-gray-800 rounded-xl p-5">
          <h2 class="font-semibold mb-3">Nodos registrados</h2>
          <table class="w-full text-sm">
            <thead><tr class="text-gray-400 text-left"><th class="py-2">Nombre</th><th>Host</th><th>Usuario</th><th>Huella host key</th><th class="text-right">Acciones</th></tr></thead>
            <tbody>
              <tr v-for="n in nodes" :key="n.id" class="border-t border-gray-800">
                <td class="py-2">{{ n.name }}</td>
                <td>{{ n.hostname }}:{{ n.ssh_port }}</td>
                <td>{{ n.ssh_user }}</td>
                <td class="font-mono text-xs text-gray-500">{{ n.host_key_fingerprint || '—' }}</td>
                <td class="text-right space-x-2">
                  <button @click="testNode(n)" class="px-2 py-1 bg-gray-700 rounded text-xs">Probar</button>
                  <button @click="syncNode(n)" class="px-2 py-1 bg-blue-700 rounded text-xs">Sincronizar</button>
                  <button @click="deleteNode(n)" class="px-2 py-1 bg-red-800 rounded text-xs">Eliminar</button>
                </td>
              </tr>
              <tr v-if="nodes.length === 0"><td colspan="5" class="py-3 text-gray-500">Sin nodos registrados.</td></tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- GUESTS -->
      <div v-show="tab === 'guests'" class="space-y-4">
        <div class="flex items-center gap-3">
          <select v-model="selectedNode" @change="loadGuests" class="px-3 py-2 bg-gray-800 rounded border border-gray-700 text-sm">
            <option :value="null">Selecciona un nodo…</option>
            <option v-for="n in nodes" :key="n.id" :value="n.id">{{ n.name }}</option>
          </select>
          <button @click="loadGuests" class="px-3 py-2 bg-gray-700 rounded text-sm">Refrescar</button>
        </div>
        <div v-for="g in guests" :key="g.id" class="bg-[#111827] border border-gray-800 rounded-xl p-4">
          <div class="flex items-center justify-between">
            <div>
              <span class="font-semibold">{{ g.name || ('VMID ' + g.vmid) }}</span>
              <span class="ml-2 text-xs px-2 py-0.5 rounded bg-gray-700">{{ g.guest_type }}</span>
              <span class="ml-1 text-xs px-2 py-0.5 rounded" :class="g.status === 'running' ? 'bg-green-800' : 'bg-gray-700'">{{ g.status }}</span>
              <span v-if="g.is_db" class="ml-1 text-xs px-2 py-0.5 rounded bg-purple-800">BD</span>
            </div>
            <span class="text-xs text-gray-500">VMID {{ g.vmid }}</span>
          </div>
          <div class="grid grid-cols-1 md:grid-cols-4 gap-2 mt-3 items-end">
            <div><label class="text-xs text-gray-400">Cores</label><input v-model.number="(res[g.id] ||= {}).cores" type="number" class="w-full px-2 py-1 bg-gray-800 rounded border border-gray-700 text-sm" /></div>
            <div><label class="text-xs text-gray-400">Memoria (MB)</label><input v-model.number="(res[g.id] ||= {}).memory" type="number" class="w-full px-2 py-1 bg-gray-800 rounded border border-gray-700 text-sm" /></div>
            <button @click="saveResources(g)" class="px-3 py-1.5 bg-cyan-600 hover:bg-cyan-700 rounded text-sm">Guardar recursos</button>
            <div class="flex gap-1">
              <input v-model="g.linked_server_id" placeholder="server_id vinculado" class="w-full px-2 py-1 bg-gray-800 rounded border border-gray-700 text-xs" />
              <button @click="linkServer(g)" class="px-2 py-1 bg-gray-700 rounded text-xs">Link</button>
            </div>
          </div>
          <div class="mt-3 border-t border-gray-800 pt-3">
            <div class="flex items-center gap-2">
              <button @click="loadSnaps(g)" class="px-2 py-1 bg-gray-700 rounded text-xs">Ver snapshots</button>
              <input v-model="newSnap[g.id]" placeholder="nombre-snapshot" class="px-2 py-1 bg-gray-800 rounded border border-gray-700 text-xs" />
              <button @click="createSnap(g)" class="px-2 py-1 bg-green-700 rounded text-xs">Crear snapshot</button>
            </div>
            <ul class="mt-2 space-y-1" v-if="snaps[g.id]">
              <li v-for="s in snaps[g.id]" :key="s.name" class="flex items-center gap-2 text-xs">
                <span class="font-mono">{{ s.name }}</span>
                <button @click="rollbackSnap(g, s.name)" class="px-2 py-0.5 bg-yellow-800 rounded">Rollback</button>
                <button @click="deleteSnap(g, s.name)" class="px-2 py-0.5 bg-red-800 rounded">Eliminar</button>
              </li>
              <li v-if="snaps[g.id].length === 0" class="text-gray-500 text-xs">Sin snapshots.</li>
            </ul>
          </div>
        </div>
        <p v-if="selectedNode && guests.length === 0" class="text-gray-500 text-sm">Sin guests. Usa "Sincronizar" en el nodo.</p>
      </div>

      <!-- BACKUPS -->
      <div v-show="tab === 'backups'" class="space-y-6">
        <div class="bg-[#111827] border border-gray-800 rounded-xl p-5">
          <h2 class="font-semibold mb-3">Nueva programación de backup</h2>
          <div class="grid grid-cols-1 md:grid-cols-3 gap-3">
            <input v-model="newSched.name" placeholder="Nombre" class="px-3 py-2 bg-gray-800 rounded border border-gray-700 text-sm" />
            <select v-model="newSched.node_id" class="px-3 py-2 bg-gray-800 rounded border border-gray-700 text-sm">
              <option :value="null">Todos los nodos</option>
              <option v-for="n in nodes" :key="n.id" :value="n.id">{{ n.name }}</option>
            </select>
            <input v-model="newSched.cron_expr" placeholder="Cron (0 3 * * *)" class="px-3 py-2 bg-gray-800 rounded border border-gray-700 text-sm" />
            <input v-model="newSched.storage" placeholder="Storage" class="px-3 py-2 bg-gray-800 rounded border border-gray-700 text-sm" />
            <select v-model="newSched.mode" class="px-3 py-2 bg-gray-800 rounded border border-gray-700 text-sm">
              <option value="snapshot">snapshot</option><option value="suspend">suspend</option><option value="stop">stop</option>
            </select>
            <label class="flex items-center gap-2 text-sm"><input type="checkbox" v-model="newSched.only_db" /> Solo servidores de BD (autodetección)</label>
          </div>
          <button @click="createSchedule" class="mt-3 px-4 py-2 bg-cyan-600 hover:bg-cyan-700 rounded text-sm">Crear programación</button>
        </div>

        <div class="bg-[#111827] border border-gray-800 rounded-xl p-5">
          <h2 class="font-semibold mb-3">Programaciones</h2>
          <table class="w-full text-sm">
            <thead><tr class="text-gray-400 text-left"><th class="py-2">Nombre</th><th>Nodo</th><th>Cron</th><th>Storage</th><th>Solo BD</th><th class="text-right"></th></tr></thead>
            <tbody>
              <tr v-for="s in schedules" :key="s.id" class="border-t border-gray-800">
                <td class="py-2">{{ s.name }}</td><td>{{ s.node_id ? nodeName(s.node_id) : 'Todos' }}</td>
                <td class="font-mono text-xs">{{ s.cron_expr }}</td><td>{{ s.storage }}</td><td>{{ s.only_db ? 'Sí' : 'No' }}</td>
                <td class="text-right"><button @click="deleteSchedule(s)" class="px-2 py-1 bg-red-800 rounded text-xs">Eliminar</button></td>
              </tr>
              <tr v-if="schedules.length === 0"><td colspan="6" class="py-3 text-gray-500">Sin programaciones.</td></tr>
            </tbody>
          </table>
        </div>

        <div class="bg-[#111827] border border-gray-800 rounded-xl p-5">
          <h2 class="font-semibold mb-3">Backup manual</h2>
          <div class="grid grid-cols-1 md:grid-cols-4 gap-3 items-end">
            <select v-model="manualRun.node_id" class="px-3 py-2 bg-gray-800 rounded border border-gray-700 text-sm">
              <option :value="null">Nodo…</option><option v-for="n in nodes" :key="n.id" :value="n.id">{{ n.name }}</option>
            </select>
            <input v-model.number="manualRun.vmid" type="number" placeholder="VMID" class="px-3 py-2 bg-gray-800 rounded border border-gray-700 text-sm" />
            <input v-model="manualRun.storage" placeholder="Storage" class="px-3 py-2 bg-gray-800 rounded border border-gray-700 text-sm" />
            <button @click="runBackup" class="px-4 py-2 bg-green-700 hover:bg-green-800 rounded text-sm">Ejecutar ahora</button>
          </div>
        </div>

        <div class="bg-[#111827] border border-gray-800 rounded-xl p-5">
          <h2 class="font-semibold mb-3">Historial de backups</h2>
          <table class="w-full text-sm">
            <thead><tr class="text-gray-400 text-left"><th class="py-2">VMID</th><th>Storage</th><th>Estado</th><th>Inicio</th></tr></thead>
            <tbody>
              <tr v-for="j in jobs" :key="j.id" class="border-t border-gray-800">
                <td class="py-2">{{ j.vmid }}</td><td>{{ j.storage }}</td>
                <td><span :class="j.status === 'ok' ? 'text-green-400' : j.status === 'error' ? 'text-red-400' : 'text-yellow-400'">{{ j.status }}</span></td>
                <td class="text-xs text-gray-500">{{ j.started_at }}</td>
              </tr>
              <tr v-if="jobs.length === 0"><td colspan="4" class="py-3 text-gray-500">Sin ejecuciones.</td></tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- MIGRACIÓN -->
      <div v-show="tab === 'migration'" class="space-y-6">
        <div class="bg-[#111827] border border-gray-800 rounded-xl p-5">
          <h2 class="font-semibold mb-1">Túnel WireGuard entre nodos</h2>
          <p class="text-xs text-gray-500 mb-3">El tráfico de migración viaja cifrado (ChaCha20-Poly1305) por el túnel.</p>
          <div class="grid grid-cols-1 md:grid-cols-3 gap-3 items-end">
            <select v-model="newLink.source_node_id" class="px-3 py-2 bg-gray-800 rounded border border-gray-700 text-sm">
              <option :value="null">Origen…</option><option v-for="n in nodes" :key="n.id" :value="n.id">{{ n.name }}</option>
            </select>
            <select v-model="newLink.target_node_id" class="px-3 py-2 bg-gray-800 rounded border border-gray-700 text-sm">
              <option :value="null">Destino…</option><option v-for="n in nodes" :key="n.id" :value="n.id">{{ n.name }}</option>
            </select>
            <button @click="createLink" class="px-4 py-2 bg-cyan-600 hover:bg-cyan-700 rounded text-sm">Establecer túnel</button>
          </div>
        </div>

        <div class="bg-[#111827] border border-gray-800 rounded-xl p-5">
          <h2 class="font-semibold mb-3">Túneles activos</h2>
          <table class="w-full text-sm">
            <thead><tr class="text-gray-400 text-left"><th class="py-2">Origen → Destino</th><th>Interfaz</th><th>IPs túnel</th><th>Estado</th><th class="text-right"></th></tr></thead>
            <tbody>
              <tr v-for="l in links" :key="l.id" class="border-t border-gray-800">
                <td class="py-2">{{ nodeName(l.source_node_id) }} → {{ nodeName(l.target_node_id) }}</td>
                <td>{{ l.wg_interface }}</td>
                <td class="font-mono text-xs">{{ l.source_tunnel_ip }} / {{ l.target_tunnel_ip }}</td>
                <td><span :class="l.status === 'up' ? 'text-green-400' : 'text-red-400'">{{ l.status }}</span></td>
                <td class="text-right"><button @click="deleteLink(l)" class="px-2 py-1 bg-red-800 rounded text-xs">Eliminar</button></td>
              </tr>
              <tr v-if="links.length === 0"><td colspan="5" class="py-3 text-gray-500">Sin túneles.</td></tr>
            </tbody>
          </table>
        </div>

        <div class="bg-[#111827] border border-gray-800 rounded-xl p-5">
          <h2 class="font-semibold mb-3">Migrar carga de trabajo</h2>
          <div class="grid grid-cols-1 md:grid-cols-5 gap-3 items-end">
            <select v-model="migration.link_id" class="px-3 py-2 bg-gray-800 rounded border border-gray-700 text-sm">
              <option :value="null">Túnel…</option>
              <option v-for="l in links" :key="l.id" :value="l.id">{{ nodeName(l.source_node_id) }} → {{ nodeName(l.target_node_id) }}</option>
            </select>
            <input v-model.number="migration.vmid" type="number" placeholder="VMID" class="px-3 py-2 bg-gray-800 rounded border border-gray-700 text-sm" />
            <select v-model="migration.guest_type" class="px-3 py-2 bg-gray-800 rounded border border-gray-700 text-sm">
              <option value="qemu">qemu (VM)</option><option value="lxc">lxc (CT)</option>
            </select>
            <input v-model="migration.storage" placeholder="Storage destino" class="px-3 py-2 bg-gray-800 rounded border border-gray-700 text-sm" />
            <button @click="migrate" class="px-4 py-2 bg-purple-700 hover:bg-purple-800 rounded text-sm">Migrar</button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
