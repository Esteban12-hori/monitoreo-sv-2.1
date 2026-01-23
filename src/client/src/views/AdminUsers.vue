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
      <div class="flex">
        <button 
          @click="router.push('/admin/groups')"
          class="bg-white dark:bg-gray-700 text-gray-700 dark:text-gray-200 border border-gray-300 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-600 px-4 py-2 rounded-md flex items-center gap-2 transition-colors mr-3"
        >
          <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
            <path d="M13 6a3 3 0 11-6 0 3 3 0 016 0zM18 8a2 2 0 11-4 0 2 2 0 014 0zM14 15a4 4 0 00-8 0v3h8v-3zM6 8a2 2 0 11-4 0 2 2 0 014 0zM16 18v-3a5.972 5.972 0 00-.75-2.906A3.005 3.005 0 0119 15v3h-3zM4.75 12.094A5.973 5.973 0 004 15v3H1v-3a3 3 0 013.75-2.906z" />
          </svg>
          Gestionar Grupos
        </button>
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
              <div class="flex flex-col gap-1.5">
                <button 
                  @click="openAssignModal(user)"
                  class="text-indigo-600 dark:text-indigo-400 hover:text-indigo-900 dark:hover:text-indigo-300 text-sm font-medium text-left flex items-center gap-1"
                >
                  <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" /></svg>
                  Acceso Servidores
                </button>
                <button 
                  @click="openRulesModal(user)"
                  class="text-purple-600 dark:text-purple-400 hover:text-purple-900 dark:hover:text-purple-300 text-sm font-medium text-left flex items-center gap-1"
                >
                  <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" /></svg>
                  Reglas Notificación
                </button>
                <button 
                  @click="openPreviewModal(user)"
                  class="text-blue-600 dark:text-blue-400 hover:text-blue-900 dark:hover:text-blue-300 text-sm font-medium text-left flex items-center gap-1"
                >
                  <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
                  Simular Alerta
                </button>
              </div>
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

    <!-- Modal Reglas Notificación -->
    <NotificationRulesModal 
      :isOpen="showRulesModal" 
      targetType="user" 
      :targetId="selectedUserRules?.id" 
      :targetName="selectedUserRules?.name || selectedUserRules?.email" 
      @close="showRulesModal = false" 
    />

    <!-- Modal Simular Alerta -->
    <div v-if="showPreviewModal" class="fixed inset-0 z-50 overflow-y-auto" aria-labelledby="modal-title" role="dialog" aria-modal="true">
      <div class="fixed inset-0 bg-gray-900/50 dark:bg-black/70 backdrop-blur-sm transition-opacity" @click="showPreviewModal = false"></div>
      <div class="flex min-h-full items-end justify-center p-4 text-center sm:items-center sm:p-0">
        <div class="relative transform overflow-hidden rounded-2xl bg-white dark:bg-gray-800 text-left shadow-2xl ring-1 ring-black/5 transition-all sm:my-8 sm:w-full sm:max-w-lg border border-gray-100 dark:border-gray-700">
          <div class="bg-white dark:bg-gray-800 px-4 pt-5 pb-4 sm:p-6 sm:pb-4">
            <h3 class="text-lg leading-6 font-semibold text-gray-900 dark:text-white flex items-center gap-2">
              <div class="p-1.5 bg-blue-100 dark:bg-blue-900/30 rounded-lg text-blue-600 dark:text-blue-400">
                <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                   <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
              Simular Recepción de Alerta
            </h3>
            <p class="mt-2 text-sm text-gray-500 dark:text-gray-400">
              Verifica si <strong>{{ selectedUserPreview?.name }}</strong> recibiría una alerta de un servidor específico.
            </p>
            
            <div class="mt-4">
               <label class="block text-sm font-medium text-gray-700 dark:text-gray-300">Seleccionar Servidor</label>
               <select v-model="previewServerId" class="mt-1 block w-full pl-3 pr-10 py-2 text-base border-gray-300 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm rounded-md dark:bg-gray-700 dark:border-gray-600 dark:text-white">
                 <option v-for="server in allServers" :key="server.server_id" :value="server.server_id">
                   {{ server.server_id }} {{ server.group_name ? `(${server.group_name})` : '' }}
                 </option>
               </select>
            </div>

            <div v-if="previewResult" class="mt-4 p-4 rounded-md" :class="previewResult.decision ? 'bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800' : 'bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800'">
                <div class="flex items-center">
                    <div class="flex-shrink-0">
                        <svg v-if="previewResult.decision" class="h-5 w-5 text-green-400" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
                            <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd" />
                        </svg>
                        <svg v-else class="h-5 w-5 text-red-400" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
                            <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd" />
                        </svg>
                    </div>
                    <div class="ml-3">
                        <h3 class="text-sm font-medium" :class="previewResult.decision ? 'text-green-800 dark:text-green-200' : 'text-red-800 dark:text-red-200'">
                            {{ previewResult.decision ? 'Recibiría Alerta' : 'No Recibiría Alerta' }}
                        </h3>
                        <div class="mt-2 text-sm" :class="previewResult.decision ? 'text-green-700 dark:text-green-300' : 'text-red-700 dark:text-red-300'">
                            <p>{{ previewResult.reason }}</p>
                            <ul class="list-disc pl-5 mt-1 space-y-1 text-xs opacity-75">
                                <li v-for="(step, i) in previewResult.trace" :key="i">{{ step }}</li>
                            </ul>
                        </div>
                    </div>
                </div>
            </div>
          </div>
          <div class="bg-gray-50 dark:bg-gray-700/50 px-4 py-3 sm:px-6 sm:flex sm:flex-row-reverse border-t border-gray-100 dark:border-gray-700">
             <button 
              @click="runPreview" 
              :disabled="!previewServerId"
              class="w-full inline-flex justify-center rounded-lg border border-transparent shadow-sm px-4 py-2 bg-indigo-600 text-base font-medium text-white hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 sm:ml-3 sm:w-auto sm:text-sm transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Probar
            </button>
            <button 
              @click="showPreviewModal = false" 
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
import NotificationRulesModal from '../components/NotificationRulesModal.vue'

const router = useRouter()
const authStore = useAuthStore()
const currentUser = computed(() => authStore.user)

const users = ref([])
const allServers = ref([])
const showCreateModal = ref(false)
const showAssignModal = ref(false)
const showRulesModal = ref(false)
const showPreviewModal = ref(false)
const showNewUserPassword = ref(false)
const selectedUser = ref(null)
const selectedUserRules = ref(null)
const selectedUserPreview = ref(null)
const previewServerId = ref('')
const previewResult = ref(null)

// Estado local de asignaciones para el modal
const tempAssignments = ref({}) // { server_id: { assigned: bool, alerts: bool } }

const newUser = ref({
  name: '',
  email: '',
  password: '',
  is_admin: false
})

const openRulesModal = (user) => {
  selectedUserRules.value = user
  showRulesModal.value = true
}

const openPreviewModal = (user) => {
    selectedUserPreview.value = user
    previewServerId.value = ''
    previewResult.value = null
    showPreviewModal.value = true
}

const runPreview = async () => {
    if (!previewServerId.value || !selectedUserPreview.value) return
    try {
        const res = await axios.post(`${API_BASE}/api/admin/alert-preview`, {
            user_id: selectedUserPreview.value.id,
            server_id: previewServerId.value
        }, { headers: authStore.getHeaders() })
        previewResult.value = res.data
    } catch (error) {
        console.error("Preview error", error)
    }
}

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
