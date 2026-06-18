<script setup>
import { ref, onMounted } from 'vue'
import axios from 'axios'
import { useAuthStore } from '../stores/auth'
import { useRouter } from 'vue-router'

const authStore = useAuthStore()
const router = useRouter()
const H = () => ({ headers: authStore.getHeaders() })

const message = ref('')
const error = ref('')
const notify = (m, isErr = false) => {
  if (isErr) { error.value = m; message.value = '' } else { message.value = m; error.value = '' }
  setTimeout(() => { message.value = ''; error.value = '' }, 5000)
}
const handleErr = (e) => {
  if (e.response && e.response.status === 401) { authStore.logout(); router.push('/login'); return }
  notify(e.response?.data?.detail || e.message, true)
}

// --- Checks agentless ---
const checks = ref([])
const newCheck = ref({ name: '', check_type: 'http', target: '', port: null, interval_seconds: 60, expected_status: 200 })
const loadChecks = async () => { try { checks.value = (await axios.get('/api/monitoring/checks', H())).data } catch (e) { handleErr(e) } }
const createCheck = async () => {
  try { await axios.post('/api/monitoring/checks', newCheck.value, H()); notify('Check creado'); newCheck.value = { name: '', check_type: 'http', target: '', port: null, interval_seconds: 60, expected_status: 200 }; await loadChecks() } catch (e) { handleErr(e) }
}
const runCheck = async (c) => { try { const r = await axios.post(`/api/monitoring/checks/${c.id}/run`, {}, H()); notify(`${c.name}: ${r.data.result.status}`); await loadChecks() } catch (e) { handleErr(e) } }
const deleteCheck = async (c) => { if (!confirm(`¿Eliminar ${c.name}?`)) return; try { await axios.delete(`/api/monitoring/checks/${c.id}`, H()); await loadChecks() } catch (e) { handleErr(e) } }

// --- Canales de notificación ---
const channels = ref([])
const newChannel = ref({ name: '', channel_type: 'slack', target: '', extra: '' })
const loadChannels = async () => { try { channels.value = (await axios.get('/api/admin/notification-channels', H())).data } catch (e) { handleErr(e) } }
const createChannel = async () => {
  try { await axios.post('/api/admin/notification-channels', newChannel.value, H()); notify('Canal creado'); newChannel.value = { name: '', channel_type: 'slack', target: '', extra: '' }; await loadChannels() } catch (e) { handleErr(e) }
}
const testChannel = async (c) => { try { const r = await axios.post(`/api/admin/notification-channels/${c.id}/test`, {}, H()); notify(`Enviado: ${r.data.detail}`) } catch (e) { handleErr(e) } }
const deleteChannel = async (c) => { if (!confirm(`¿Eliminar ${c.name}?`)) return; try { await axios.delete(`/api/admin/notification-channels/${c.id}`, H()); await loadChannels() } catch (e) { handleErr(e) } }

// --- Mantenimiento ---
const purging = ref(false)
const purge = async () => {
  if (!confirm('¿Purgar históricos según la política de retención?')) return
  purging.value = true
  try { const r = await axios.post('/api/admin/maintenance/purge', {}, H()); notify(`Eliminados: ${r.data.deleted.metrics} métricas, ${r.data.deleted.check_results} resultados`) }
  catch (e) { handleErr(e) } finally { purging.value = false }
}

const statusColor = (s) => s === 'up' ? 'text-green-400' : s === 'down' ? 'text-red-400' : 'text-gray-400'

onMounted(async () => { await loadChecks(); await loadChannels() })
</script>

<template>
  <div class="min-h-screen bg-[#0b1120] text-gray-200 py-10 px-4 sm:px-8">
    <div class="max-w-6xl mx-auto space-y-6">
      <div class="flex items-center justify-between">
        <h1 class="text-2xl font-bold text-white">Monitoreo &amp; Notificaciones</h1>
        <router-link to="/dashboard" class="text-cyan-400 hover:text-cyan-300 text-sm">← Dashboard</router-link>
      </div>
      <div v-if="message" class="bg-green-900/30 border border-green-700 text-green-300 px-4 py-2 rounded-lg text-sm">{{ message }}</div>
      <div v-if="error" class="bg-red-900/30 border border-red-700 text-red-300 px-4 py-2 rounded-lg text-sm">{{ error }}</div>

      <!-- Checks agentless -->
      <div class="bg-[#111827] border border-gray-800 rounded-xl p-5">
        <h2 class="font-semibold mb-1">Checks agentless (HTTP / TCP / ICMP)</h2>
        <p class="text-xs text-gray-500 mb-3">El servidor monitoriza endpoints sin instalar agente en el destino.</p>
        <div class="grid grid-cols-1 md:grid-cols-6 gap-2 items-end">
          <input v-model="newCheck.name" placeholder="Nombre" class="px-2 py-1.5 bg-gray-800 rounded border border-gray-700 text-sm md:col-span-1" />
          <select v-model="newCheck.check_type" class="px-2 py-1.5 bg-gray-800 rounded border border-gray-700 text-sm">
            <option value="http">HTTP</option><option value="tcp">TCP</option><option value="icmp">ICMP</option>
          </select>
          <input v-model="newCheck.target" placeholder="URL / host" class="px-2 py-1.5 bg-gray-800 rounded border border-gray-700 text-sm md:col-span-2" />
          <input v-model.number="newCheck.port" type="number" placeholder="Puerto (TCP)" class="px-2 py-1.5 bg-gray-800 rounded border border-gray-700 text-sm" />
          <button @click="createCheck" class="px-3 py-1.5 bg-cyan-600 hover:bg-cyan-700 rounded text-sm">Añadir</button>
        </div>
        <table class="w-full text-sm mt-4">
          <thead><tr class="text-gray-400 text-left"><th class="py-2">Nombre</th><th>Tipo</th><th>Objetivo</th><th>Estado</th><th>Latencia</th><th class="text-right"></th></tr></thead>
          <tbody>
            <tr v-for="c in checks" :key="c.id" class="border-t border-gray-800">
              <td class="py-2">{{ c.name }}</td><td class="uppercase text-xs">{{ c.check_type }}</td>
              <td class="font-mono text-xs">{{ c.target }}{{ c.port ? ':' + c.port : '' }}</td>
              <td :class="statusColor(c.last_status)">{{ c.last_status || '—' }}</td>
              <td>{{ c.last_latency_ms != null ? c.last_latency_ms + ' ms' : '—' }}</td>
              <td class="text-right space-x-2">
                <button @click="runCheck(c)" class="px-2 py-1 bg-gray-700 rounded text-xs">Probar</button>
                <button @click="deleteCheck(c)" class="px-2 py-1 bg-red-800 rounded text-xs">Eliminar</button>
              </td>
            </tr>
            <tr v-if="checks.length === 0"><td colspan="6" class="py-3 text-gray-500">Sin checks configurados.</td></tr>
          </tbody>
        </table>
      </div>

      <!-- Canales -->
      <div class="bg-[#111827] border border-gray-800 rounded-xl p-5">
        <h2 class="font-semibold mb-1">Canales de notificación</h2>
        <p class="text-xs text-gray-500 mb-3">Reciben las alertas además del correo. El secreto se guarda cifrado.</p>
        <div class="grid grid-cols-1 md:grid-cols-5 gap-2 items-end">
          <input v-model="newChannel.name" placeholder="Nombre" class="px-2 py-1.5 bg-gray-800 rounded border border-gray-700 text-sm" />
          <select v-model="newChannel.channel_type" class="px-2 py-1.5 bg-gray-800 rounded border border-gray-700 text-sm">
            <option value="slack">Slack</option><option value="discord">Discord</option><option value="telegram">Telegram</option><option value="webhook">Webhook</option>
          </select>
          <input v-model="newChannel.target" :placeholder="newChannel.channel_type === 'telegram' ? 'Token del bot' : 'Webhook URL'" class="px-2 py-1.5 bg-gray-800 rounded border border-gray-700 text-sm md:col-span-2" />
          <input v-if="newChannel.channel_type === 'telegram'" v-model="newChannel.extra" placeholder="chat_id" class="px-2 py-1.5 bg-gray-800 rounded border border-gray-700 text-sm" />
          <button @click="createChannel" class="px-3 py-1.5 bg-cyan-600 hover:bg-cyan-700 rounded text-sm">Añadir</button>
        </div>
        <table class="w-full text-sm mt-4">
          <thead><tr class="text-gray-400 text-left"><th class="py-2">Nombre</th><th>Tipo</th><th>Activo</th><th class="text-right"></th></tr></thead>
          <tbody>
            <tr v-for="c in channels" :key="c.id" class="border-t border-gray-800">
              <td class="py-2">{{ c.name }}</td><td class="capitalize">{{ c.channel_type }}</td><td>{{ c.enabled ? 'Sí' : 'No' }}</td>
              <td class="text-right space-x-2">
                <button @click="testChannel(c)" class="px-2 py-1 bg-gray-700 rounded text-xs">Probar</button>
                <button @click="deleteChannel(c)" class="px-2 py-1 bg-red-800 rounded text-xs">Eliminar</button>
              </td>
            </tr>
            <tr v-if="channels.length === 0"><td colspan="4" class="py-3 text-gray-500">Sin canales configurados.</td></tr>
          </tbody>
        </table>
      </div>

      <!-- Mantenimiento -->
      <div class="bg-[#111827] border border-gray-800 rounded-xl p-5 flex items-center justify-between">
        <div>
          <h2 class="font-semibold">Retención de datos</h2>
          <p class="text-xs text-gray-500">Purga históricos antiguos según la política configurada (env <code>METRICS_RETENTION_DAYS</code>).</p>
        </div>
        <button @click="purge" :disabled="purging" class="px-4 py-2 bg-yellow-700 hover:bg-yellow-800 rounded text-sm disabled:opacity-50">{{ purging ? 'Purgando…' : 'Purgar ahora' }}</button>
      </div>
    </div>
  </div>
</template>
