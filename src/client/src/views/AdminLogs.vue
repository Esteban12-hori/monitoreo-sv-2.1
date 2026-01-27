<script setup>
import { ref, onMounted } from 'vue'
import { useAuthStore } from '../stores/auth'
import axios from 'axios'

const authStore = useAuthStore()
const logs = ref([])
const loading = ref(false)
const lines = ref(100)

const fetchLogs = async () => {
  loading.value = true
  try {
    const res = await axios.get(`/api/admin/logs?lines=${lines.value}`, {
      headers: authStore.getHeaders()
    })
    logs.value = res.data.logs || []
  } catch (e) {
    console.error(e)
    alert("Error fetching logs")
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchLogs()
})
</script>

<template>
  <div class="min-h-screen bg-[#0b1120] text-gray-100 p-8">
    <div class="max-w-7xl mx-auto">
      <div class="flex justify-between items-center mb-6">
        <h1 class="text-2xl font-bold text-white">Server Logs</h1>
        <div class="flex gap-4">
             <select v-model="lines" @change="fetchLogs" class="bg-gray-800 border border-gray-700 text-gray-300 text-sm rounded-lg p-2.5 focus:ring-cyan-500 focus:border-cyan-500">
                <option :value="50">50 lines</option>
                <option :value="100">100 lines</option>
                <option :value="500">500 lines</option>
                <option :value="1000">1000 lines</option>
            </select>
            <button @click="fetchLogs" class="px-4 py-2 bg-cyan-600 hover:bg-cyan-700 rounded-lg text-white font-medium transition-colors">
                Refresh
            </button>
             <router-link to="/" class="px-4 py-2 bg-gray-800 hover:bg-gray-700 rounded-lg text-gray-300 font-medium transition-colors">
                Back to Dashboard
            </router-link>
        </div>
      </div>

      <div class="bg-[#111827] rounded-xl border border-gray-800 shadow-lg overflow-hidden">
        <div class="p-4 bg-gray-900/50 border-b border-gray-800 flex justify-between items-center">
            <span class="text-sm text-gray-400">Displaying last {{ lines }} lines</span>
             <span v-if="loading" class="text-cyan-400 text-sm animate-pulse">Loading...</span>
        </div>
        <div class="p-4 overflow-x-auto">
            <pre class="text-xs font-mono text-gray-300 whitespace-pre-wrap"><code v-if="logs.length">{{ logs.join('') }}</code><code v-else class="text-gray-500">No logs available or empty file.</code></pre>
        </div>
      </div>
    </div>
  </div>
</template>
