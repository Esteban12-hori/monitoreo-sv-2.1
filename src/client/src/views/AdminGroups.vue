<template>
  <div class="space-y-6">
    <div class="flex justify-between items-center">
      <div class="flex items-center gap-3">
        <button
          @click="router.push('/admin/users')"
          class="inline-flex items-center px-3 py-1.5 border border-gray-300 dark:border-gray-600 rounded-md text-xs font-medium text-gray-700 dark:text-gray-200 bg-white dark:bg-gray-700 hover:bg-gray-50 dark:hover:bg-gray-600 transition-colors"
        >
          <svg class="h-4 w-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 19l-7-7m0 0l7-7m-7 7h18" />
          </svg>
          Volver a Usuarios
        </button>
        <h1 class="text-3xl font-bold text-gray-900 dark:text-white">Gestión de Grupos</h1>
      </div>
      <button 
        @click="openCreateModal"
        class="bg-indigo-600 hover:bg-indigo-700 text-white px-4 py-2 rounded-md flex items-center gap-2 transition-colors"
      >
        <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
          <path fill-rule="evenodd" d="M10 3a1 1 0 011 1v5h5a1 1 0 110 2h-5v5a1 1 0 11-2 0v-5H4a1 1 0 110-2h5V4a1 1 0 011-1z" clip-rule="evenodd" />
        </svg>
        Nuevo Grupo
      </button>
    </div>

    <!-- Lista de Grupos -->
    <div class="bg-white dark:bg-gray-800 shadow rounded-lg overflow-hidden">
      <table class="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
        <thead class="bg-gray-50 dark:bg-gray-700">
          <tr>
            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">Nombre</th>
            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">Descripción</th>
            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">Miembros</th>
            <th class="px-6 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">Acciones</th>
          </tr>
        </thead>
        <tbody class="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
          <tr v-for="group in groups" :key="group.id">
            <td class="px-6 py-4 whitespace-nowrap">
              <div class="text-sm font-medium text-gray-900 dark:text-white">{{ group.name }}</div>
            </td>
            <td class="px-6 py-4 whitespace-nowrap">
              <div class="text-sm text-gray-500 dark:text-gray-400">{{ group.description || '-' }}</div>
            </td>
            <td class="px-6 py-4 whitespace-nowrap">
              <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200">
                {{ group.user_count }} usuarios
              </span>
            </td>
            <td class="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
              <button 
                @click="openEditModal(group)"
                class="text-indigo-600 dark:text-indigo-400 hover:text-indigo-900 dark:hover:text-indigo-300 mr-4"
              >
                Editar
              </button>
              <button 
                @click="openRulesModal(group)"
                class="text-purple-600 dark:text-purple-400 hover:text-purple-900 dark:hover:text-purple-300 mr-4"
              >
                Reglas
              </button>
              <button 
                @click="deleteGroup(group)"
                class="text-red-600 hover:text-red-900 dark:hover:text-red-400"
              >
                Eliminar
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Modal Crear/Editar Grupo -->
    <div v-if="showModal" class="fixed inset-0 z-50 overflow-y-auto" aria-modal="true">
        <div class="fixed inset-0 bg-gray-900/50 dark:bg-black/70 backdrop-blur-sm transition-opacity" @click="showModal = false"></div>
        <div class="flex min-h-full items-end justify-center p-4 text-center sm:items-center sm:p-0">
            <div class="relative transform overflow-hidden rounded-lg bg-white dark:bg-gray-800 text-left shadow-xl transition-all sm:my-8 sm:w-full sm:max-w-lg border border-gray-100 dark:border-gray-700">
                <div class="bg-white dark:bg-gray-800 px-4 pt-5 pb-4 sm:p-6 sm:pb-4">
                    <h3 class="text-lg font-medium leading-6 text-gray-900 dark:text-white mb-4">
                        {{ isEditing ? 'Editar Grupo' : 'Crear Nuevo Grupo' }}
                    </h3>
                    <div class="space-y-4">
                        <div>
                            <label class="block text-sm font-medium text-gray-700 dark:text-gray-300">Nombre</label>
                            <input v-model="form.name" type="text" class="mt-1 block w-full rounded-md border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm py-2">
                        </div>
                        <div>
                            <label class="block text-sm font-medium text-gray-700 dark:text-gray-300">Descripción</label>
                            <input v-model="form.description" type="text" class="mt-1 block w-full rounded-md border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm py-2">
                        </div>
                        
                        <div>
                            <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Miembros</label>
                            <div class="max-h-48 overflow-y-auto border border-gray-200 dark:border-gray-700 rounded-md p-2 space-y-2">
                                <div v-for="user in users" :key="user.id" class="flex items-center">
                                    <input 
                                        type="checkbox" 
                                        :id="'user-' + user.id" 
                                        :value="user.id" 
                                        v-model="form.user_ids"
                                        class="h-4 w-4 text-indigo-600 focus:ring-indigo-500 border-gray-300 rounded"
                                    >
                                    <label :for="'user-' + user.id" class="ml-2 block text-sm text-gray-900 dark:text-gray-300 cursor-pointer select-none">
                                        {{ user.name || user.email }}
                                        <span class="text-gray-500 text-xs ml-1" v-if="user.name">({{ user.email }})</span>
                                    </label>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
                <div class="bg-gray-50 dark:bg-gray-700/50 px-4 py-3 sm:px-6 sm:flex sm:flex-row-reverse">
                    <button 
                        @click="submitForm" 
                        type="button" 
                        class="w-full inline-flex justify-center rounded-md border border-transparent shadow-sm px-4 py-2 bg-indigo-600 text-base font-medium text-white hover:bg-indigo-700 focus:outline-none sm:ml-3 sm:w-auto sm:text-sm"
                    >
                        {{ isEditing ? 'Guardar Cambios' : 'Crear' }}
                    </button>
                    <button 
                        @click="showModal = false" 
                        type="button" 
                        class="mt-3 w-full inline-flex justify-center rounded-md border border-gray-300 shadow-sm px-4 py-2 bg-white text-base font-medium text-gray-700 hover:bg-gray-50 focus:outline-none sm:mt-0 sm:ml-3 sm:w-auto sm:text-sm dark:bg-gray-800 dark:text-gray-200 dark:border-gray-600"
                    >
                        Cancelar
                    </button>
                </div>
            </div>
        </div>
    </div>

    <!-- Modal Reglas -->
    <NotificationRulesModal 
      :isOpen="showRulesModal" 
      targetType="group" 
      :targetId="selectedGroupRules?.id" 
      :targetName="selectedGroupRules?.name" 
      @close="showRulesModal = false" 
    />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue';
import { useRouter } from 'vue-router';
import { useAuthStore } from '../stores/auth';
import NotificationRulesModal from '../components/NotificationRulesModal.vue';
import axios from 'axios';

const router = useRouter();
const authStore = useAuthStore();

const groups = ref<any[]>([]);
const users = ref<any[]>([]);
const showModal = ref(false);
const showRulesModal = ref(false);
const selectedGroupRules = ref<any>(null);
const isEditing = ref(false);
const editingId = ref<number | null>(null);

const form = ref({
    name: '',
    description: '',
    user_ids: [] as number[]
});

const API_BASE = ''; // Proxy handles it

const fetchGroups = async () => {
    try {
        const res = await axios.get(`${API_BASE}/api/admin/groups`, { headers: authStore.getHeaders() });
        groups.value = res.data;
    } catch (e) {
        console.error("Error fetching groups", e);
    }
};

const fetchUsers = async () => {
    try {
        const res = await axios.get(`${API_BASE}/api/admin/users`, { headers: authStore.getHeaders() });
        users.value = res.data;
    } catch (e) {
        console.error("Error fetching users", e);
    }
};

const openCreateModal = () => {
    isEditing.value = false;
    editingId.value = null;
    form.value = { name: '', description: '', user_ids: [] };
    showModal.value = true;
};

const openEditModal = (group: any) => {
    isEditing.value = true;
    editingId.value = group.id;
    // user_ids should be available in group object thanks to our backend update
    form.value = { 
        name: group.name, 
        description: group.description, 
        user_ids: group.user_ids ? [...group.user_ids] : [] 
    };
    showModal.value = true;
};

const submitForm = async () => {
    try {
        if (isEditing.value && editingId.value) {
            await axios.put(`${API_BASE}/api/admin/groups/${editingId.value}`, form.value, { headers: authStore.getHeaders() });
        } else {
            await axios.post(`${API_BASE}/api/admin/groups`, form.value, { headers: authStore.getHeaders() });
        }
        showModal.value = false;
        fetchGroups();
    } catch (e) {
        console.error(e);
        alert("Error al guardar grupo");
    }
};

const deleteGroup = async (group: any) => {
    if (!confirm(`¿Eliminar grupo ${group.name}?`)) return;
    try {
        await axios.delete(`${API_BASE}/api/admin/groups/${group.id}`, { headers: authStore.getHeaders() });
        fetchGroups();
    } catch (e) {
        console.error(e);
    }
};

const openRulesModal = (group: any) => {
    selectedGroupRules.value = group;
    showRulesModal.value = true;
};

onMounted(() => {
    fetchGroups();
    fetchUsers();
});
</script>
