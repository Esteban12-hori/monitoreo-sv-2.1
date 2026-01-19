<template>
  <div class="space-y-6">
    <!-- Breadcrumb & Header -->
    <div
      class="flex flex-col lg:flex-row justify-between items-start lg:items-center gap-4
             bg-indigo-200/80 dark:bg-indigo-900/60 border border-indigo-200 dark:border-indigo-700
             rounded-2xl shadow-sm px-4 py-3 sm:px-6 sm:py-4 backdrop-blur"
    >
      <div class="w-full">
        <div class="flex items-center gap-3 mb-2">
          <button
            @click="router.back()"
            class="inline-flex items-center px-2.5 py-1.5 border border-gray-300 dark:border-gray-600 rounded-md text-xs font-medium text-gray-700 dark:text-gray-200 bg-white dark:bg-gray-800 hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors shadow-sm"
          >
            <svg class="h-4 w-4 mr-1.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 19l-7-7m0 0l7-7m-7 7h18" />
            </svg>
            Volver
          </button>
          <nav class="flex items-center gap-2 text-sm text-gray-500 dark:text-gray-400">
            <router-link to="/dashboard" class="hover:text-indigo-600 dark:hover:text-indigo-400 transition-colors">
              <svg class="w-4 h-4 inline-block -mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
              </svg>
              Dashboard
            </router-link>
            <span>/</span>
            <span class="font-medium text-gray-700 dark:text-gray-300 truncate max-w-[150px] sm:max-w-xs">{{ serverId }}</span>
          </nav>
        </div>
        <div class="flex flex-wrap items-center gap-3 mb-2">
          <h1 class="text-2xl sm:text-3xl font-bold text-gray-900 dark:text-white tracking-tight break-all">{{ serverId }}</h1>
          <span v-if="serverInfo?.group_name" class="px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 border border-gray-200 dark:border-gray-600">
            {{ serverInfo.group_name }}
          </span>
          <span class="relative flex h-3 w-3">
            <span v-if="isOnline" class="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>
            <span class="relative inline-flex rounded-full h-3 w-3" :class="isOnline ? 'bg-green-500' : 'bg-red-500'"></span>
          </span>
        </div>
        <p class="text-sm text-gray-500 flex flex-wrap items-center gap-y-1 gap-x-2">
          <span class="flex items-center gap-1">
            <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <span class="hidden sm:inline">Última actualización:</span> <span class="font-medium text-gray-700 dark:text-gray-300">{{ lastUpdate }}</span>
          </span>
          <span class="hidden sm:inline text-gray-300 dark:text-gray-600">|</span>
          <span class="flex items-center gap-1">
            <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
               <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            Uptime: <span class="font-medium text-gray-700 dark:text-gray-300">{{ latestMetrics ? formatUptime(latestMetrics.uptime) : '-' }}</span>
          </span>
        </p>
      </div>
      
      <div class="w-full lg:w-auto flex items-center gap-3 bg-white dark:bg-gray-800 p-2 rounded-lg shadow-sm border border-gray-100 dark:border-gray-700">
        <button 
          @click="openConfigModal"
          class="hidden sm:inline-flex items-center px-3 py-2 border border-transparent text-sm leading-4 font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 transition-colors shadow-sm"
        >
          <svg class="h-4 w-4 mr-1.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
          </svg>
          Config
        </button>
        <div class="h-6 w-px bg-gray-300 dark:bg-gray-600 mx-1 hidden sm:block"></div>
        <label class="text-sm font-medium text-gray-700 dark:text-gray-300 pl-2 whitespace-nowrap">Rango:</label>
        <select 
          v-model="timeRange" 
          @change="fetchHistory"
          class="block w-full lg:w-40 rounded-md border-gray-300 dark:border-gray-600 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm dark:bg-gray-700 dark:text-white"
        >
          <option :value="1">Última hora</option>
          <option :value="5">Últimas 5 horas</option>
          <option :value="7">Últimas 7 horas</option>
          <option :value="8">Últimas 8 horas</option>
          <option :value="10">Últimas 10 horas</option>
          <option :value="24">Últimas 24 horas</option>
        </select>
        <button @click="fetchHistory" class="p-2 text-gray-400 hover:text-indigo-600 dark:hover:text-indigo-400 transition-colors" title="Actualizar ahora">
          <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
        </button>
      </div>
    </div>

    <!-- Loading Skeleton -->
    <div v-if="isLoading && !latestMetrics" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 animate-pulse">
       <div class="h-32 bg-gray-200 dark:bg-gray-700 rounded-2xl" v-for="i in 4" :key="i"></div>
    </div>

    <!-- KPI Cards -->
    <div v-else-if="latestMetrics" class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-5 gap-6">
      <!-- CPU Card -->
      <div class="bg-white dark:bg-gray-800 p-5 rounded-2xl shadow-sm border relative overflow-hidden group hover:shadow-md transition-shadow" :class="getCardBorderClass(latestMetrics.cpu.total)">
        <div class="flex justify-between items-start mb-4">
          <div>
            <p class="text-xs font-semibold text-gray-500 uppercase tracking-wider">CPU</p>
            <h3 class="text-2xl font-bold text-gray-900 dark:text-white mt-1">{{ latestMetrics.cpu.total.toFixed(1) }}%</h3>
          </div>
          <div class="p-2 bg-blue-50 dark:bg-blue-900/20 rounded-lg text-blue-600 dark:text-blue-400">
            <svg class="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 3v2m6-2v2M9 19v2m6-2v2M5 9H3m2 6H3m18-6h-2m2 6h-2M7 19h10a2 2 0 002-2V7a2 2 0 00-2-2H7a2 2 0 00-2 2v10a2 2 0 002 2zM9 9h6v6H9V9z" />
            </svg>
          </div>
        </div>
        <div class="w-full bg-gray-100 dark:bg-gray-700 rounded-full h-1.5 mb-2">
          <div class="bg-blue-500 h-1.5 rounded-full transition-all duration-500" :style="{ width: latestMetrics.cpu.total + '%' }"></div>
        </div>
        <p class="text-xs text-gray-500">{{ (latestMetrics.cpu.per_core || []).length }} Núcleos detectados</p>
      </div>

      <!-- Memory Card -->
      <div class="bg-white dark:bg-gray-800 p-5 rounded-2xl shadow-sm border relative overflow-hidden group hover:shadow-md transition-shadow" :class="getCardBorderClass((latestMetrics.memory.used / latestMetrics.memory.total) * 100)">
        <div class="flex justify-between items-start mb-4">
          <div>
            <p class="text-xs font-semibold text-gray-500 uppercase tracking-wider">Memoria</p>
            <h3 class="text-2xl font-bold text-gray-900 dark:text-white mt-1">{{ formatBytes(latestMetrics.memory.used) }}</h3>
          </div>
          <div class="p-2 bg-green-50 dark:bg-green-900/20 rounded-lg text-green-600 dark:text-green-400">
            <svg class="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
          </div>
        </div>
        <div class="w-full bg-gray-100 dark:bg-gray-700 rounded-full h-1.5 mb-2">
          <div class="bg-green-500 h-1.5 rounded-full transition-all duration-500" :style="{ width: (latestMetrics.memory.used / latestMetrics.memory.total * 100) + '%' }"></div>
        </div>
        <p class="text-xs text-gray-500">Total: {{ formatBytes(latestMetrics.memory.total) }}</p>
      </div>

      <!-- Disk Card -->
      <div class="bg-white dark:bg-gray-800 p-5 rounded-2xl shadow-sm border relative overflow-hidden group hover:shadow-md transition-shadow" :class="getCardBorderClass(latestMetrics.disk.percent, 80, 90)">
        <div class="flex justify-between items-start mb-4">
          <div>
            <p class="text-xs font-semibold text-gray-500 uppercase tracking-wider">Disco</p>
            <h3 class="text-2xl font-bold text-gray-900 dark:text-white mt-1">{{ latestMetrics.disk.percent.toFixed(1) }}%</h3>
          </div>
          <div class="p-2 bg-yellow-50 dark:bg-yellow-900/20 rounded-lg text-yellow-600 dark:text-yellow-400">
            <svg class="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4" />
            </svg>
          </div>
        </div>
        <div class="w-full bg-gray-100 dark:bg-gray-700 rounded-full h-1.5 mb-2">
          <div class="bg-yellow-500 h-1.5 rounded-full transition-all duration-500" :style="{ width: latestMetrics.disk.percent + '%' }"></div>
        </div>
        <p class="text-xs text-gray-500">Libre: {{ formatBytes(latestMetrics.disk.free) }}</p>
      </div>

      <!-- Network Card -->
      <div class="bg-white dark:bg-gray-800 p-5 rounded-2xl shadow-sm border border-gray-100 dark:border-gray-700 relative overflow-hidden group hover:shadow-md transition-shadow">
        <div class="flex justify-between items-start mb-4">
          <div>
            <p class="text-xs font-semibold text-gray-500 uppercase tracking-wider">Red</p>
            <div class="flex flex-col mt-1">
                 <span class="text-sm font-bold text-gray-900 dark:text-white flex items-center gap-1">
                    <span class="text-blue-500 text-xs">▲</span> {{ formatBytes(latestMetrics.net_sent_rate || 0) }}/s
                 </span>
                 <span class="text-sm font-bold text-gray-900 dark:text-white flex items-center gap-1">
                    <span class="text-green-500 text-xs">▼</span> {{ formatBytes(latestMetrics.net_recv_rate || 0) }}/s
                 </span>
            </div>
          </div>
          <div class="p-2 bg-indigo-50 dark:bg-indigo-900/20 rounded-lg text-indigo-600 dark:text-indigo-400">
            <svg class="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4" />
            </svg>
          </div>
        </div>
        <div class="w-full bg-gray-100 dark:bg-gray-700 rounded-full h-1.5 mb-2 overflow-hidden flex">
             <div class="bg-blue-500 h-full animate-pulse" style="width: 50%"></div>
             <div class="bg-green-500 h-full animate-pulse" style="width: 50%"></div>
        </div>
        <p class="text-xs text-gray-500">
          Total:
          {{ latestMetrics.network ? formatBytes((latestMetrics.network.bytes_sent || 0) + (latestMetrics.network.bytes_recv || 0)) : '0 Bytes' }}
        </p>
      </div>

      <!-- Redis Card -->
      <div class="bg-white dark:bg-gray-800 p-5 rounded-2xl shadow-sm border relative overflow-hidden group hover:shadow-md transition-shadow" :class="isRedisRunning ? 'border-red-500 dark:border-red-500' : 'border-gray-100 dark:border-gray-700'">
        <div class="flex justify-between items-start mb-4">
          <div>
            <p class="text-xs font-semibold text-gray-500 uppercase tracking-wider">Redis</p>
            <h3 class="text-2xl font-bold mt-1" :class="isRedisRunning ? 'text-gray-900 dark:text-white' : 'text-gray-400 dark:text-gray-500'">
              {{ isRedisRunning ? 'Activo' : 'Inactivo' }}
            </h3>
          </div>
          <div class="p-2 bg-red-50 dark:bg-red-900/20 rounded-lg text-red-600 dark:text-red-400">
            <svg class="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
               <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
            </svg>
          </div>
        </div>
        <div class="w-full bg-gray-100 dark:bg-gray-700 rounded-full h-1.5 mb-2">
          <div class="bg-red-500 h-1.5 rounded-full transition-all duration-500" :style="{ width: isRedisRunning ? '100%' : '0%' }"></div>
        </div>
        <p class="text-xs text-gray-500">{{ isRedisRunning ? 'Servicio detectado' : 'No detectado' }}</p>
      </div>

      <!-- Docker Card -->
      <div class="bg-white dark:bg-gray-800 p-5 rounded-2xl shadow-sm border border-gray-100 dark:border-gray-700 relative overflow-hidden group hover:shadow-md transition-shadow">
        <div class="flex justify-between items-start mb-4">
          <div>
            <p class="text-xs font-semibold text-gray-500 uppercase tracking-wider">Docker</p>
            <h3 class="text-2xl font-bold text-gray-900 dark:text-white mt-1">{{ latestMetrics.docker.running_containers }}</h3>
          </div>
          <div class="p-2 bg-purple-50 dark:bg-purple-900/20 rounded-lg text-purple-600 dark:text-purple-400">
            <svg class="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
            </svg>
          </div>
        </div>
        <div class="w-full bg-gray-100 dark:bg-gray-700 rounded-full h-1.5 mb-2">
          <div class="bg-purple-500 h-1.5 rounded-full transition-all duration-500" :style="{ width: (latestMetrics.docker.running_containers > 0 ? 100 : 0) + '%' }"></div>
        </div>
        <p class="text-xs text-gray-500">Total: {{ latestMetrics.docker.total_containers }} Contenedores</p>
      </div>
    </div>

    <!-- Empty State -->
    <div v-else class="mt-6 bg-white dark:bg-gray-800 rounded-2xl shadow-sm border border-gray-100 dark:border-gray-700 p-8 text-center">
      <h2 class="text-lg font-semibold text-gray-900 dark:text-white mb-2">Sin datos de métricas aún</h2>
      <p class="text-sm text-gray-500 dark:text-gray-400 mb-1">
        Todavía no hemos recibido información reciente del servidor <span class="font-mono">{{ serverId }}</span>.
      </p>
      <p class="text-sm text-gray-500 dark:text-gray-400">
        Verifica que el agente esté instalado y ejecutándose, o espera unos segundos y vuelve a actualizar.
      </p>
    </div>

    <!-- Charts Section -->
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <!-- CPU Chart -->
      <div class="bg-white dark:bg-gray-800 p-6 rounded-2xl shadow-sm border border-gray-100 dark:border-gray-700">
        <div class="flex items-center justify-between mb-6">
          <h3 class="text-lg font-semibold text-gray-900 dark:text-white flex items-center gap-2">
            <span class="w-2 h-6 bg-blue-500 rounded-sm"></span>
            Histórico CPU
          </h3>
        </div>
        <div class="h-64 relative">
           <Line v-if="chartDataCpu" :data="chartDataCpu" :options="chartOptions" />
           <div v-else class="absolute inset-0 flex items-center justify-center text-gray-400">
             <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
           </div>
        </div>
      </div>

      <!-- Memory Chart -->
      <div class="bg-white dark:bg-gray-800 p-6 rounded-2xl shadow-sm border border-gray-100 dark:border-gray-700">
        <div class="flex items-center justify-between mb-6">
          <h3 class="text-lg font-semibold text-gray-900 dark:text-white flex items-center gap-2">
             <span class="w-2 h-6 bg-green-500 rounded-sm"></span>
             Histórico Memoria
          </h3>
        </div>
        <div class="h-64 relative">
           <Line v-if="chartDataMem" :data="chartDataMem" :options="chartOptions" />
           <div v-else class="absolute inset-0 flex items-center justify-center text-gray-400">
              <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-green-500"></div>
           </div>
        </div>
      </div>

      <!-- Disk Chart -->
      <div class="bg-white dark:bg-gray-800 p-6 rounded-2xl shadow-sm border border-gray-100 dark:border-gray-700">
        <div class="flex items-center justify-between mb-6">
          <h3 class="text-lg font-semibold text-gray-900 dark:text-white flex items-center gap-2">
             <span class="w-2 h-6 bg-yellow-500 rounded-sm"></span>
             Histórico Disco
          </h3>
        </div>
        <div class="h-64 relative">
           <Line v-if="chartDataDisk" :data="chartDataDisk" :options="chartOptions" />
           <div v-else class="absolute inset-0 flex items-center justify-center text-gray-400">
              <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-yellow-500"></div>
           </div>
        </div>
      </div>

      <!-- Network Chart -->
      <div class="bg-white dark:bg-gray-800 p-6 rounded-2xl shadow-sm border border-gray-100 dark:border-gray-700">
        <div class="flex items-center justify-between mb-6">
          <h3 class="text-lg font-semibold text-gray-900 dark:text-white flex items-center gap-2">
             <span class="w-2 h-6 bg-indigo-500 rounded-sm"></span>
             Histórico Red
          </h3>
        </div>
        <div class="h-64 relative">
           <Line v-if="chartDataNetwork" :data="chartDataNetwork" :options="chartOptions" />
           <div v-else class="absolute inset-0 flex items-center justify-center text-gray-400">
              <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-500"></div>
           </div>
        </div>
      </div>
    </div>

    <!-- Docker Details -->
    <div class="bg-white dark:bg-gray-800 rounded-2xl shadow-sm border border-gray-100 dark:border-gray-700 overflow-hidden">
      <div class="px-6 py-4 border-b border-gray-100 dark:border-gray-700 flex justify-between items-center">
        <h3 class="text-lg font-semibold text-gray-900 dark:text-white flex items-center gap-2">
          <svg class="w-5 h-5 text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
          </svg>
          Contenedores Docker
        </h3>
        <span v-if="latestMetrics && latestMetrics.docker.containers" class="text-xs font-medium bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 px-2.5 py-0.5 rounded-full">
          {{ parseDocker(latestMetrics.docker.containers).length }} Total
        </span>
      </div>
      <div class="overflow-x-auto">
        <table class="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
          <thead class="bg-gray-50 dark:bg-gray-700/50">
            <tr>
              <th scope="col" class="px-4 sm:px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Nombre / ID</th>
              <th scope="col" class="px-4 sm:px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Imagen</th>
              <th scope="col" class="px-4 sm:px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Estado</th>
            </tr>
          </thead>
          <tbody class="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
            <tr v-if="!latestMetrics" class="animate-pulse">
               <td colspan="3" class="px-6 py-4 text-center text-sm text-gray-500">Cargando contenedores...</td>
            </tr>
            <tr v-else-if="!latestMetrics.docker.containers || parseDocker(latestMetrics.docker.containers).length === 0">
               <td colspan="3" class="px-6 py-8 text-center text-sm text-gray-500 dark:text-gray-400 flex flex-col items-center gap-2">
                 <svg class="w-8 h-8 text-gray-300" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                   <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4" />
                 </svg>
                 No hay contenedores reportados
               </td>
            </tr>
            <tr v-for="(container, idx) in (latestMetrics ? parseDocker(latestMetrics.docker.containers) : [])" :key="idx" class="hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors">
              <td class="px-4 sm:px-6 py-4 whitespace-nowrap">
                <div class="flex items-center">
                  <div class="flex-shrink-0 h-8 w-8 rounded bg-blue-100 dark:bg-blue-900/30 flex items-center justify-center text-blue-600 dark:text-blue-400">
                    <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                       <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 8h14M5 8a2 2 0 110-4h14a2 2 0 110 4M5 8v10a2 2 0 002 2h10a2 2 0 002-2V8m-9 4h4" />
                    </svg>
                  </div>
                  <div class="ml-3 sm:ml-4">
                    <div class="text-sm font-medium text-gray-900 dark:text-white max-w-[120px] sm:max-w-none truncate">{{ container.name }}</div>
                    <div class="text-xs text-gray-500 font-mono">{{ container.id ? container.id.substring(0, 12) : '' }}</div>
                  </div>
                </div>
              </td>
              <td class="px-4 sm:px-6 py-4 whitespace-nowrap">
                <div class="text-sm text-gray-500 dark:text-gray-300 max-w-[100px] sm:max-w-xs truncate" :title="container.image">{{ container.image || '-' }}</div>
              </td>
              <td class="px-4 sm:px-6 py-4 whitespace-nowrap">
                <span class="px-2.5 py-0.5 inline-flex text-xs leading-5 font-semibold rounded-full bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200 border border-green-200 dark:border-green-800">
                  <span class="w-1.5 h-1.5 bg-green-500 rounded-full mr-1.5 self-center"></span>
                  Running
                </span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Processes Details -->
    <div class="bg-white dark:bg-gray-800 rounded-2xl shadow-sm border border-gray-100 dark:border-gray-700 overflow-hidden mt-6">
      <div class="px-6 py-4 border-b border-gray-100 dark:border-gray-700 flex justify-between items-center">
        <h3 class="text-lg font-semibold text-gray-900 dark:text-white flex items-center gap-2">
          <svg class="w-5 h-5 text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
          Procesos Top (CPU/Mem)
        </h3>
        <span v-if="latestMetrics && latestMetrics.processes" class="text-xs font-medium bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 px-2.5 py-0.5 rounded-full">
          {{ parseProcesses(latestMetrics.processes).length }} Procesos
        </span>
      </div>
      <div class="overflow-x-auto">
        <table class="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
          <thead class="bg-gray-50 dark:bg-gray-700/50">
            <tr>
              <th scope="col" class="px-4 sm:px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">PID</th>
              <th scope="col" class="px-4 sm:px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Nombre</th>
              <th scope="col" class="px-4 sm:px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Usuario</th>
              <th scope="col" class="px-4 sm:px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">CPU %</th>
              <th scope="col" class="px-4 sm:px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Mem %</th>
            </tr>
          </thead>
          <tbody class="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
            <tr v-if="!latestMetrics" class="animate-pulse">
               <td colspan="5" class="px-6 py-4 text-center text-sm text-gray-500">Cargando procesos...</td>
            </tr>
            <tr v-else-if="!latestMetrics.processes || parseProcesses(latestMetrics.processes).length === 0">
               <td colspan="5" class="px-6 py-8 text-center text-sm text-gray-500 dark:text-gray-400 flex flex-col items-center gap-2">
                 No hay procesos reportados
               </td>
            </tr>
            <tr v-for="(proc, idx) in (latestMetrics ? parseProcesses(latestMetrics.processes) : [])" :key="idx" class="hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors">
              <td class="px-4 sm:px-6 py-4 whitespace-nowrap text-sm font-mono text-gray-500 dark:text-gray-400">
                {{ proc.pid }}
              </td>
              <td class="px-4 sm:px-6 py-4 whitespace-nowrap">
                <div class="text-sm font-medium text-gray-900 dark:text-white">{{ proc.name }}</div>
              </td>
              <td class="px-4 sm:px-6 py-4 whitespace-nowrap">
                <div class="text-sm text-gray-500 dark:text-gray-300">{{ proc.username }}</div>
              </td>
              <td class="px-4 sm:px-6 py-4 whitespace-nowrap">
                <span class="px-2 py-0.5 text-xs font-medium rounded-full" :class="proc.cpu_percent > 50 ? 'bg-red-100 text-red-800' : 'bg-gray-100 text-gray-800'">
                  {{ proc.cpu_percent.toFixed(1) }}%
                </span>
              </td>
              <td class="px-4 sm:px-6 py-4 whitespace-nowrap">
                <span class="px-2 py-0.5 text-xs font-medium rounded-full" :class="proc.memory_percent > 50 ? 'bg-red-100 text-red-800' : 'bg-gray-100 text-gray-800'">
                   {{ proc.memory_percent.toFixed(1) }}%
                </span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <div class="mt-6 bg-white dark:bg-gray-900 rounded-2xl shadow-lg border border-purple-100/60 dark:border-purple-800/60 overflow-hidden">
      <div class="px-6 py-4 bg-gradient-to-r from-purple-600 via-indigo-600 to-blue-500 flex justify-between items-center">
        <h3 class="text-lg font-semibold text-white flex items-center gap-2">
          <svg class="w-5 h-5 text-purple-100" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19.428 15.428a2 2 0 00-1.022-.547l-2.387-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z" />
          </svg>
          Puertos y Servicios Detectados
        </h3>
        <span v-if="latestMetrics && latestMetrics.services" class="text-xs font-semibold bg-white/15 text-purple-50 px-3 py-1 rounded-full backdrop-blur">
          {{ servicesSummary.total }} activos
        </span>
      </div>
      <div class="px-6 py-3 flex flex-wrap gap-2 border-b border-purple-100/60 dark:border-purple-800/60 bg-purple-50/70 dark:bg-purple-900/20">
        <span class="inline-flex items-center gap-1 text-xs font-medium text-purple-900 dark:text-purple-100 bg-white/80 dark:bg-purple-900/60 px-2.5 py-1 rounded-full">
          <span class="w-1.5 h-1.5 rounded-full bg-purple-500"></span>
          Total: {{ servicesSummary.total }}
        </span>
        <span class="inline-flex items-center gap-1 text-xs font-medium text-amber-900 dark:text-amber-50 bg-amber-50/80 dark:bg-amber-900/50 px-2.5 py-1 rounded-full">
          <span class="w-1.5 h-1.5 rounded-full bg-amber-500"></span>
          Expuestos: {{ servicesSummary.publicCount }}
        </span>
        <span class="inline-flex items-center gap-1 text-xs font-medium text-red-900 dark:text-red-50 bg-red-50/80 dark:bg-red-900/60 px-2.5 py-1 rounded-full">
          <span class="w-1.5 h-1.5 rounded-full bg-red-500"></span>
          Críticos: {{ servicesSummary.critical }}
        </span>
      </div>
      <div class="overflow-x-auto">
        <table class="min-w-full divide-y divide-gray-200 dark:divide-gray-800">
          <thead class="bg-gray-50 dark:bg-gray-800">
            <tr>
              <th scope="col" class="px-4 sm:px-6 py-3 text-left text-xs font-semibold text-gray-600 dark:text-gray-300 uppercase tracking-wider">Servicio / Proceso</th>
              <th scope="col" class="px-4 sm:px-6 py-3 text-left text-xs font-semibold text-gray-600 dark:text-gray-300 uppercase tracking-wider">Interfaz</th>
              <th scope="col" class="px-4 sm:px-6 py-3 text-left text-xs font-semibold text-gray-600 dark:text-gray-300 uppercase tracking-wider">Puerto</th>
              <th scope="col" class="px-4 sm:px-6 py-3 text-left text-xs font-semibold text-gray-600 dark:text-gray-300 uppercase tracking-wider">Protocolo</th>
              <th v-if="isAdmin" scope="col" class="px-4 sm:px-6 py-3 text-right text-xs font-semibold text-gray-600 dark:text-gray-300 uppercase tracking-wider">Acción</th>
            </tr>
          </thead>
          <tbody class="bg-white dark:bg-gray-900 divide-y divide-gray-100 dark:divide-gray-800">
            <tr v-if="!latestMetrics" class="animate-pulse">
               <td colspan="4" class="px-6 py-4 text-center text-sm text-gray-500">Cargando servicios...</td>
            </tr>
            <tr v-else-if="!latestMetrics.services || parseServices(latestMetrics.services).length === 0">
               <td colspan="4" class="px-6 py-8 text-center text-sm text-gray-500 dark:text-gray-400 flex flex-col items-center gap-2">
                 <svg class="w-8 h-8 text-gray-300" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                 </svg>
                 No hay servicios detectados
               </td>
            </tr>
            <tr v-for="(svc, idx) in (latestMetrics ? parseServices(latestMetrics.services) : [])" :key="idx" class="hover:bg-purple-50/60 dark:hover:bg-purple-900/25 transition-colors">
              <td class="px-4 sm:px-6 py-4 whitespace-nowrap">
                <div class="flex items-center">
                  <div class="flex-shrink-0 h-8 w-8 rounded bg-purple-100 dark:bg-purple-900/30 flex items-center justify-center text-purple-600 dark:text-purple-400">
                    <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                       <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 12h14M5 12a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v4a2 2 0 01-2 2M5 12a2 2 0 00-2 2v4a2 2 0 002 2h14a2 2 0 002-2v-4a2 2 0 00-2-2m-2-4h.01M17 16h.01" />
                    </svg>
                  </div>
                  <div class="ml-3 sm:ml-4">
                    <div class="text-sm font-semibold text-gray-900 dark:text-white capitalize tracking-tight">{{ svc.name }}</div>
                  </div>
                </div>
              </td>
              <td class="px-4 sm:px-6 py-4 whitespace-nowrap">
                <div class="inline-flex items-center gap-1 text-xs font-mono px-2 py-0.5 rounded-full" :class="getIpBadgeClasses(svc.ip)">
                  <span class="w-1.5 h-1.5 rounded-full" :class="svc.ip === '0.0.0.0' || !svc.ip ? 'bg-amber-500' : 'bg-emerald-500'"></span>
                  <span>{{ svc.ip || '*' }}</span>
                </div>
              </td>
              <td class="px-4 sm:px-6 py-4 whitespace-nowrap">
                <div class="text-sm font-mono border px-2 py-0.5 rounded inline-flex items-center gap-1" :class="getPortBadgeClasses(svc.port)">
                  {{ svc.port }}
                </div>
              </td>
              <td class="px-4 sm:px-6 py-4 whitespace-nowrap">
                <span class="px-2.5 py-0.5 inline-flex text-xs leading-5 font-semibold rounded-full border uppercase" :class="getProtoBadgeClasses(svc.proto)">
                  {{ svc.proto || 'tcp' }}
                </span>
              </td>
              <td class="px-4 sm:px-6 py-4 whitespace-nowrap text-right" v-if="isAdmin">
                <div class="flex flex-wrap justify-end gap-2">
                  <button
                    type="button"
                    class="inline-flex items-center px-3 py-1.5 text-xs font-medium rounded-full border border-gray-300 text-gray-700 hover:bg-gray-100 dark:text-gray-200 dark:border-gray-500 dark:hover:bg-gray-800 transition-colors"
                    @click="copyServiceEndpoint(svc)"
                  >
                    Copiar IP:puerto
                  </button>
                  <button
                    type="button"
                    class="inline-flex items-center px-3 py-1.5 text-xs font-medium rounded-full border border-indigo-500 text-indigo-600 hover:bg-indigo-50 dark:text-indigo-300 dark:border-indigo-400 dark:hover:bg-indigo-900/30 transition-colors"
                    @click="openServiceInfo(svc)"
                  >
                    Buscar servicio
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Configuration Modal -->
    <div v-if="isConfigModalOpen" class="fixed inset-0 z-50 overflow-y-auto" aria-labelledby="modal-title" role="dialog" aria-modal="true">
      <div class="flex items-end justify-center min-h-screen pt-4 px-4 pb-20 text-center sm:block sm:p-0">
        <div class="fixed inset-0 bg-gray-900 bg-opacity-75 transition-opacity" aria-hidden="true" @click="isConfigModalOpen = false"></div>
        <span class="hidden sm:inline-block sm:align-middle sm:h-screen" aria-hidden="true">&#8203;</span>
        <div class="inline-block align-bottom bg-white dark:bg-gray-800 rounded-lg text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:align-middle sm:max-w-lg w-full border border-gray-200 dark:border-gray-700">
          <div class="bg-white dark:bg-gray-800 px-4 pt-5 pb-4 sm:p-6 sm:pb-4">
            <div class="sm:flex sm:items-start">
              <div class="mx-auto flex-shrink-0 flex items-center justify-center h-12 w-12 rounded-full bg-indigo-100 dark:bg-indigo-900/30 sm:mx-0 sm:h-10 sm:w-10">
                <svg class="h-6 w-6 text-indigo-600 dark:text-indigo-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                </svg>
              </div>
              <div class="mt-3 text-center sm:mt-0 sm:ml-4 sm:text-left w-full">
                <h3 class="text-lg leading-6 font-medium text-gray-900 dark:text-white" id="modal-title">
                  Configuración del Servidor
                </h3>
                <div class="mt-2">
                  <p class="text-sm text-gray-500 dark:text-gray-400 mb-4">
                    Ajusta el intervalo de reporte para este servidor.
                  </p>
                  <div>
                    <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Intervalo de Actualización</label>
                    <select 
                      v-model="tempInterval"
                      class="mt-1 block w-full pl-3 pr-10 py-2 text-base border-gray-300 dark:border-gray-600 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm rounded-md dark:bg-gray-700 dark:text-white"
                    >
                      <option v-for="opt in intervalOptions" :key="opt.value" :value="opt.value">
                        {{ opt.label }}
                      </option>
                    </select>
                    <p class="mt-1 text-xs text-gray-500 dark:text-gray-400">
                      Selecciona '0' para pausar el monitoreo.
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </div>
          <div class="bg-gray-50 dark:bg-gray-700/50 px-4 py-3 sm:px-6 sm:flex sm:flex-row-reverse">
            <button 
              type="button" 
              class="w-full inline-flex justify-center rounded-md border border-transparent shadow-sm px-4 py-2 bg-indigo-600 text-base font-medium text-white hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 sm:ml-3 sm:w-auto sm:text-sm disabled:opacity-50"
              @click="saveInterval"
              :disabled="savingInterval"
            >
              <svg v-if="savingInterval" class="animate-spin -ml-1 mr-2 h-4 w-4 text-white" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              {{ savingInterval ? 'Guardando...' : 'Guardar Cambios' }}
            </button>
            <button 
              type="button" 
              class="mt-3 w-full inline-flex justify-center rounded-md border border-gray-300 dark:border-gray-600 shadow-sm px-4 py-2 bg-white dark:bg-gray-800 text-base font-medium text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 sm:mt-0 sm:ml-3 sm:w-auto sm:text-sm"
              @click="isConfigModalOpen = false"
            >
              Cancelar
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

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
const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'

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
const tempInterval = ref(5)
const savingInterval = ref(false)
let pollTimer = null

const isAdmin = computed(() => authStore.isAdmin)

const isRedisRunning = computed(() => {
  if (!latestMetrics.value || !latestMetrics.value.services) return false
  const services = parseServices(latestMetrics.value.services)
  return services.some(s => s.port === 6379 || (s.name && s.name.toLowerCase().includes('redis')))
})

const intervalOptions = [
  { value: 0, label: 'Desactivado' },
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

const openConfigModal = () => {
  if (serverInfo.value) {
    tempInterval.value = serverInfo.value.report_interval ?? 300
    isConfigModalOpen.value = true
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
    legend: {
      display: false
    },
    tooltip: {
      backgroundColor: 'rgba(17, 24, 39, 0.95)',
      titleColor: '#f3f4f6',
      bodyColor: '#e5e7eb',
      borderColor: 'rgba(75, 85, 99, 0.4)',
      borderWidth: 1,
      padding: 12,
      cornerRadius: 8,
      displayColors: true,
      boxPadding: 4,
      callbacks: {
        label: (context) => {
          const val = context.parsed.y.toFixed(2)
          if (context.dataset.label.includes('MB/s')) return ` ${context.dataset.label}: ${val} MB/s`
          return ` ${context.dataset.label}: ${val}%`
        }
      }
    }
  },
  scales: {
    y: {
      beginAtZero: true,
      grid: { 
        color: 'rgba(156, 163, 175, 0.05)',
        drawBorder: false 
      },
      ticks: { 
        color: '#9ca3af', 
        font: { size: 10, family: "'Inter', sans-serif" },
        padding: 8
      },
      border: { display: false }
    },
    x: {
      grid: { display: false },
      ticks: { 
        color: '#9ca3af',
        maxTicksLimit: 8,
        font: { size: 10, family: "'Inter', sans-serif" },
        maxRotation: 0,
        padding: 8
      },
      border: { display: false }
    }
  },
  elements: {
    line: {
      tension: 0.4, // Smooth curves
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
    console.error("Error parsing docker JSON", e)
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

const getPortBadgeClasses = (port) => {
  const p = Number(port)
  if ([22, 80, 443, 3389, 5900, 8080].includes(p)) {
    return 'bg-red-50 text-red-700 dark:bg-red-900/40 dark:text-red-200 border-red-200 dark:border-red-700'
  }
  if (p > 0 && p < 1024) {
    return 'bg-amber-50 text-amber-800 dark:bg-amber-900/40 dark:text-amber-100 border-amber-200 dark:border-amber-700'
  }
  return 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-200 border-gray-300 dark:border-gray-600'
}

const getProtoBadgeClasses = (proto) => {
  const p = (proto || 'tcp').toString().toLowerCase()
  if (p === 'udp') {
    return 'bg-sky-50 text-sky-800 dark:bg-sky-900/40 dark:text-sky-100 border-sky-200 dark:border-sky-700'
  }
  return 'bg-blue-100 text-blue-800 dark:bg-blue-900/50 dark:text-blue-100 border-blue-200 dark:border-blue-700'
}

const getCardBorderClass = (val, warning = 75, critical = 90) => {
  if (val >= critical) return 'border-red-500 dark:border-red-500'
  if (val >= warning) return 'border-amber-500 dark:border-amber-500'
  return 'border-gray-100 dark:border-gray-700'
}

const getIpBadgeClasses = (ip) => {
  if (!ip || ip === '0.0.0.0' || ip === '::') {
    return 'bg-amber-50 text-amber-800 dark:bg-amber-900/40 dark:text-amber-100 border border-amber-200 dark:border-amber-700'
  }
  return 'bg-emerald-50 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-100 border border-emerald-200 dark:border-emerald-700'
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
      
      // Calculate Network Rate (Current)
      // Prefer server-sent rate if available
      if (last.network && (last.network.sent_rate !== undefined || last.network.recv_rate !== undefined)) {
          latestMetrics.value.net_sent_rate = last.network.sent_rate || 0
          latestMetrics.value.net_recv_rate = last.network.recv_rate || 0
      } else if (data.length >= 2) {
         // Fallback to client-side calculation
         const prev = data[data.length - 2]
         const timeDiff = (new Date(last.ts) - new Date(prev.ts)) / 1000
         if (timeDiff > 0 && last.network && prev.network) {
            latestMetrics.value.net_sent_rate = (last.network.bytes_sent - prev.network.bytes_sent) / timeDiff
            latestMetrics.value.net_recv_rate = (last.network.bytes_recv - prev.network.bytes_recv) / timeDiff
         }
      }

      lastUpdate.value = new Date(last.ts).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
      
      // Check online status (within last 5 mins)
      const lastTs = new Date(last.ts).getTime()
      const now = new Date().getTime()
      const diffMinutes = (now - lastTs) / 1000 / 60
      // Use reported interval if available, otherwise default to 5 min
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
          borderColor: '#3b82f6',
          backgroundColor: (context) => {
            const ctx = context.chart.ctx;
            return gradient(ctx, 'rgba(59, 130, 246, 0.5)', 'rgba(59, 130, 246, 0.0)')
          },
          fill: true,
          tension: 0.4
        }]
      }
      
      chartDataMem.value = {
        labels,
        datasets: [{
          label: 'Memoria',
          data: data.map(d => (d.memory.used / d.memory.total * 100)),
          borderColor: '#10b981',
          backgroundColor: (context) => {
            const ctx = context.chart.ctx;
            return gradient(ctx, 'rgba(16, 185, 129, 0.5)', 'rgba(16, 185, 129, 0.0)')
          },
          fill: true,
          tension: 0.4
        }]
      }
      
      chartDataDisk.value = {
        labels,
        datasets: [{
          label: 'Disco',
          data: data.map(d => d.disk.percent),
          borderColor: '#f59e0b',
          backgroundColor: (context) => {
            const ctx = context.chart.ctx;
            return gradient(ctx, 'rgba(245, 158, 11, 0.5)', 'rgba(245, 158, 11, 0.0)')
          },
          fill: true,
          tension: 0.4
        }]
      }

      // Network Chart Data
      const netSent = []
      const netRecv = []
      for (let i = 0; i < data.length; i++) {
         const curr = data[i]
         // Prefer server-sent rate if available
         if (curr.network && (curr.network.sent_rate !== undefined || curr.network.recv_rate !== undefined)) {
            const sentMB = (curr.network.sent_rate || 0) / 1024 / 1024
            const recvMB = (curr.network.recv_rate || 0) / 1024 / 1024
            netSent.push(sentMB)
            netRecv.push(recvMB)
         } else {
             if (i === 0) {
                 netSent.push(0)
                 netRecv.push(0)
                 continue
             }
             const prev = data[i-1]
             const tDiff = (new Date(curr.ts) - new Date(prev.ts)) / 1000
             
             if (tDiff > 0 && curr.network && prev.network) {
                 // MB/s
                 const sentMB = ((curr.network.bytes_sent - prev.network.bytes_sent) / tDiff) / 1024 / 1024
                 const recvMB = ((curr.network.bytes_recv - prev.network.bytes_recv) / tDiff) / 1024 / 1024
                 netSent.push(sentMB > 0 ? sentMB : 0)
                 netRecv.push(recvMB > 0 ? recvMB : 0)
             } else {
                 netSent.push(0)
                 netRecv.push(0)
             }
         }
      }

      chartDataNetwork.value = {
        labels,
        datasets: [
          {
            label: 'Subida (MB/s)',
            data: netSent,
            borderColor: '#3b82f6',
            backgroundColor: (context) => {
                const ctx = context.chart.ctx;
                return gradient(ctx, 'rgba(59, 130, 246, 0.5)', 'rgba(59, 130, 246, 0.0)')
            },
            fill: true,
            tension: 0.4
          },
          {
            label: 'Bajada (MB/s)',
            data: netRecv,
            borderColor: '#10b981',
            backgroundColor: (context) => {
                const ctx = context.chart.ctx;
                return gradient(ctx, 'rgba(16, 185, 129, 0.5)', 'rgba(16, 185, 129, 0.0)')
            },
            fill: true,
            tension: 0.4
          }
        ]
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
