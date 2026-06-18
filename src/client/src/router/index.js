import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import Login from '../views/Login.vue'
import Dashboard from '../views/Dashboard.vue'
import Setup from '../views/Setup.vue'
import AdminUsers from '../views/AdminUsers.vue'
import AdminGroups from '../views/AdminGroups.vue'
import AdminLogs from '../views/AdminLogs.vue'
import ProxmoxManager from '../views/ProxmoxManager.vue'
import ServerDetail from '../views/ServerDetail.vue'
import ChangePasswordModal from '../components/ChangePasswordModal.vue'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: Login,
    meta: { guest: true }
  },
  {
    path: '/',
    redirect: '/dashboard'
  },
  {
    path: '/dashboard',
    name: 'Dashboard',
    component: Dashboard,
    meta: { requiresAuth: true }
  },
  {
    path: '/server/:id',
    name: 'ServerDetail',
    component: ServerDetail,
    meta: { requiresAuth: true }
  },
  {
    path: '/setup',
    name: 'Setup',
    component: Setup,
    meta: { requiresAuth: true, requiresAdmin: true }
  },
  {
    path: '/admin/users',
    name: 'AdminUsers',
    component: AdminUsers,
    meta: { requiresAuth: true, requiresAdmin: true }
  },
  {
    path: '/admin/groups',
    name: 'AdminGroups',
    component: AdminGroups,
    meta: { requiresAuth: true, requiresAdmin: true }
  },
  {
    path: '/admin/logs',
    name: 'AdminLogs',
    component: AdminLogs,
    meta: { requiresAuth: true, requiresAdmin: true }
  },
  {
    path: '/admin/proxmox',
    name: 'ProxmoxManager',
    component: ProxmoxManager,
    meta: { requiresAuth: true, requiresAdmin: true }
  },
  {
    path: '/change-password',
    name: 'ChangePassword',
    component: ChangePasswordModal,
    meta: { requiresAuth: true }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach((to, from, next) => {
  const authStore = useAuthStore()

  if (to.meta.requiresAuth && !authStore.isAuthenticated) {
    next('/login')
  } else if (authStore.isAuthenticated && authStore.mustChangePassword && to.path !== '/change-password') {
    next('/change-password')
  } else if (to.meta.guest && authStore.isAuthenticated) {
    next('/dashboard')
  } else if (to.meta.requiresAdmin && !authStore.user?.is_admin) {
    next('/dashboard') // Redirigir si no es admin
  } else {
    next()
  }
})

export default router
