<template>
  <div v-if="isOpen" class="fixed inset-0 z-50 overflow-y-auto" role="dialog" aria-modal="true">
    <div class="fixed inset-0 bg-gray-900/50 dark:bg-black/70 backdrop-blur-sm transition-opacity" @click="close"></div>

    <div class="flex min-h-full items-end justify-center p-4 text-center sm:items-center sm:p-0">
      <div class="relative transform overflow-hidden rounded-2xl bg-white dark:bg-gray-800 text-left shadow-2xl ring-1 ring-black/5 transition-all sm:my-8 sm:w-full sm:max-w-3xl border border-gray-100 dark:border-gray-700">
        <div class="bg-white dark:bg-gray-800 px-4 pt-5 pb-4 sm:p-6">
          <h3 class="text-lg leading-6 font-semibold text-gray-900 dark:text-white flex items-center gap-2">
            <div class="p-1.5 bg-purple-100 dark:bg-purple-900/30 rounded-lg text-purple-600 dark:text-purple-400">
              <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
              </svg>
            </div>
            Reglas de Notificación - {{ targetName }}
          </h3>
          <p class="mt-2 text-sm text-gray-500 dark:text-gray-400">
            Define qué alertas debe recibir o bloquear este {{ targetType === 'user' ? 'usuario' : 'grupo' }}.
          </p>

          <!-- Add Rule Form -->
          <div class="mt-6 bg-gray-50 dark:bg-gray-700/30 rounded-lg p-4 border border-gray-200 dark:border-gray-700">
            <h4 class="text-sm font-medium text-gray-900 dark:text-white mb-3">Nueva Regla</h4>
            <div class="grid grid-cols-1 sm:grid-cols-3 gap-4 items-end">
              <div>
                <label class="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">Alcance</label>
                <select v-model="newRule.server_id" class="block w-full rounded-md border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-sm py-2">
                  <option :value="null">Global (Todos los servidores)</option>
                  <option v-for="server in servers" :key="server.server_id" :value="server.server_id">
                    {{ server.server_id }}
                  </option>
                </select>
              </div>
              <div>
                <label class="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">Acción</label>
                <select v-model="newRule.action" class="block w-full rounded-md border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-sm py-2">
                  <option value="ALLOW">PERMITIR (ALLOW)</option>
                  <option value="BLOCK">BLOQUEAR (BLOCK)</option>
                </select>
              </div>
              <button 
                @click="addRule"
                class="w-full inline-flex justify-center rounded-md border border-transparent shadow-sm px-4 py-2 bg-indigo-600 text-base font-medium text-white hover:bg-indigo-700 focus:outline-none sm:text-sm transition-colors"
                :disabled="loading"
              >
                {{ loading ? 'Guardando...' : 'Añadir Regla' }}
              </button>
            </div>
          </div>

          <!-- Rules List -->
          <div class="mt-6">
            <h4 class="text-sm font-medium text-gray-900 dark:text-white mb-3">Reglas Activas</h4>
            <div v-if="loadingRules" class="text-center py-4 text-gray-500">Cargando reglas...</div>
            <div v-else-if="rules.length === 0" class="text-center py-8 bg-gray-50 dark:bg-gray-700/30 rounded-lg border border-dashed border-gray-300 dark:border-gray-600 text-gray-500">
              No hay reglas definidas. Se usará el comportamiento por defecto.
            </div>
            <div v-else class="overflow-hidden shadow ring-1 ring-black ring-opacity-5 rounded-lg">
              <table class="min-w-full divide-y divide-gray-300 dark:divide-gray-700">
                <thead class="bg-gray-50 dark:bg-gray-700">
                  <tr>
                    <th scope="col" class="py-3.5 pl-4 pr-3 text-left text-sm font-semibold text-gray-900 dark:text-white sm:pl-6">Alcance</th>
                    <th scope="col" class="px-3 py-3.5 text-left text-sm font-semibold text-gray-900 dark:text-white">Acción</th>
                    <th scope="col" class="relative py-3.5 pl-3 pr-4 sm:pr-6">
                      <span class="sr-only">Eliminar</span>
                    </th>
                  </tr>
                </thead>
                <tbody class="divide-y divide-gray-200 dark:divide-gray-700 bg-white dark:bg-gray-800">
                  <tr v-for="rule in rules" :key="rule.id">
                    <td class="whitespace-nowrap py-4 pl-4 pr-3 text-sm font-medium text-gray-900 dark:text-white sm:pl-6">
                      <span v-if="!rule.server_id" class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200">
                        Global
                      </span>
                      <span v-else class="inline-flex items-center gap-1">
                        <svg class="h-4 w-4 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 12h14M5 12a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v4a2 2 0 01-2 2M5 12a2 2 0 00-2 2v4a2 2 0 002 2h14a2 2 0 002-2v-4a2 2 0 00-2-2m-2-4h.01M17 16h.01" />
                        </svg>
                        {{ rule.server_id }}
                      </span>
                    </td>
                    <td class="whitespace-nowrap px-3 py-4 text-sm text-gray-500 dark:text-gray-300">
                      <span 
                        class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium"
                        :class="rule.action === 'ALLOW' ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200' : 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200'"
                      >
                        {{ rule.action === 'ALLOW' ? 'PERMITIR' : 'BLOQUEAR' }}
                      </span>
                    </td>
                    <td class="relative whitespace-nowrap py-4 pl-3 pr-4 text-right text-sm font-medium sm:pr-6">
                      <button @click="deleteRule(rule.id)" class="text-red-600 hover:text-red-900 dark:hover:text-red-400">Eliminar</button>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>
        <div class="bg-gray-50 dark:bg-gray-700/50 px-4 py-3 sm:px-6 sm:flex sm:flex-row-reverse border-t border-gray-100 dark:border-gray-700">
          <button 
            @click="close" 
            type="button" 
            class="mt-3 w-full inline-flex justify-center rounded-md border border-gray-300 shadow-sm px-4 py-2 bg-white text-base font-medium text-gray-700 hover:bg-gray-50 focus:outline-none sm:mt-0 sm:ml-3 sm:w-auto sm:text-sm dark:bg-gray-800 dark:text-gray-200 dark:border-gray-600 dark:hover:bg-gray-700 transition-colors"
          >
            Cerrar
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue';
import { useAuthStore } from '../stores/auth';

const props = defineProps<{
  isOpen: boolean;
  targetType: 'user' | 'group';
  targetId: number;
  targetName: string;
}>();

const emit = defineEmits(['close']);
const authStore = useAuthStore();

const rules = ref<any[]>([]);
const servers = ref<any[]>([]);
const loading = ref(false);
const loadingRules = ref(false);

const newRule = ref({
  server_id: null as string | null,
  action: 'ALLOW'
});

const fetchRules = async () => {
  loadingRules.value = true;
  try {
    const params = new URLSearchParams();
    if (props.targetType === 'user') params.append('user_id', props.targetId.toString());
    else params.append('group_id', props.targetId.toString());

    const res = await fetch(`${authStore.apiBase}/api/admin/notification-rules?${params.toString()}`, {
      headers: { 'Authorization': `Bearer ${authStore.token}` }
    });
    if (res.ok) {
      rules.value = await res.json();
    }
  } catch (e) {
    console.error(e);
  } finally {
    loadingRules.value = false;
  }
};

const fetchServers = async () => {
  try {
    const res = await fetch(`${authStore.apiBase}/api/servers`, {
      headers: { 'Authorization': `Bearer ${authStore.token}` }
    });
    if (res.ok) {
      servers.value = await res.json();
    }
  } catch (e) {
    console.error(e);
  }
};

const addRule = async () => {
  loading.value = true;
  try {
    const payload = {
      server_id: newRule.value.server_id,
      action: newRule.value.action,
      user_id: props.targetType === 'user' ? props.targetId : null,
      group_id: props.targetType === 'group' ? props.targetId : null
    };

    const res = await fetch(`${authStore.apiBase}/api/admin/notification-rules`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${authStore.token}`
      },
      body: JSON.stringify(payload)
    });

    if (res.ok) {
      await fetchRules();
      newRule.value.server_id = null; // Reset form
      newRule.value.action = 'ALLOW';
    } else {
        const err = await res.json();
        alert(err.detail || 'Error creating rule');
    }
  } catch (e) {
    console.error(e);
  } finally {
    loading.value = false;
  }
};

const deleteRule = async (ruleId: number) => {
  if (!confirm('¿Estás seguro de eliminar esta regla?')) return;
  try {
    const res = await fetch(`${authStore.apiBase}/api/admin/notification-rules/${ruleId}`, {
      method: 'DELETE',
      headers: { 'Authorization': `Bearer ${authStore.token}` }
    });
    if (res.ok) {
      await fetchRules();
    }
  } catch (e) {
    console.error(e);
  }
};

const close = () => {
  emit('close');
};

watch(() => props.isOpen, (val) => {
  if (val) {
    fetchRules();
    fetchServers();
  }
});
</script>
