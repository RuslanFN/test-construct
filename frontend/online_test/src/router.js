import { createRouter, createWebHashHistory } from 'vue-router';

import { authState, restoreSession } from './auth';

import Login from './user/Login.vue';
import UserProfile from './user/UserProfile.vue';
import Results from './user/Results.vue';
import Constructor from './constructor/Constructor.vue';
import TakeTest from './public/TakeTest.vue';
import Admin from './admin/Admin.vue';

const routes = [
  { path: '/', redirect: { name: 'profile' } },
  { path: '/login', name: 'login', component: Login, meta: { public: true, guestOnly: true } },
  { path: '/profile', name: 'profile', component: UserProfile, meta: { requiresAuth: true } },
  { path: '/editor/:id', name: 'editor', component: Constructor, meta: { requiresAuth: true } },
  { path: '/results/:id', name: 'results', component: Results, meta: { requiresAuth: true } },
  { path: '/admin', name: 'admin', component: Admin, meta: { requiresAuth: true, requiresAdmin: true } },
  { path: '/take/:token', name: 'take', component: TakeTest, props: true, meta: { public: true } },
  { path: '/:pathMatch(.*)*', redirect: { name: 'profile' } },
];

const router = createRouter({
  history: createWebHashHistory(),
  routes,
});

// Гард: перед каждым переходом гарантируем, что сессия восстановлена.
router.beforeEach(async (to) => {
  if (!authState.initialized) {
    await restoreSession();
  }

  const authed = !!authState.user;

  // защищённый маршрут без авторизации -> на логин (с запоминанием, куда шли)
  if (to.meta.requiresAuth && !authed) {
    return { name: 'login', query: { redirect: to.fullPath } };
  }

  // на логин уже авторизованному -> в профиль
  if (to.meta.guestOnly && authed) {
    return { name: 'profile' };
  }

  // только для админа
  if (to.meta.requiresAdmin && authState.user?.role !== 'admin') {
    return { name: 'profile' };
  }

  return true;
});

export default router;
