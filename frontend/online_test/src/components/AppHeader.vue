<script setup>
import { computed } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { authState, logout } from '../auth';

const route = useRoute();
const router = useRouter();

const userLabel = computed(() => {
  const u = authState.user;
  if (!u) return '';
  return [u.last_name, u.first_name].filter(Boolean).join(' ') || u.username;
});

const isAdmin = computed(() => authState.user?.role === 'admin');

async function doLogout() {
  await logout();
  router.push({ name: 'login' });
}
</script>

<template>
  <header class="app-header">
    <div class="app-header-inner">
      <div class="brand" @click="router.push({ name: 'profile' })">Онлайн-тесты</div>
      <div class="header-right">
        <RouterLink
          v-if="route.name === 'profile'"
          :to="{ name: 'editor', params: { id: 'new' } }"
          class="new-test-btn"
        >
          + Новый тест
        </RouterLink>
        <RouterLink v-if="isAdmin" :to="{ name: 'admin' }" class="admin-link">Админ-панель</RouterLink>
        <span class="header-user" v-if="userLabel">{{ userLabel }}</span>
        <button class="logout-btn" @click="doLogout">Выйти</button>
      </div>
    </div>
  </header>
</template>

<style>
.app-header {
  position: sticky;
  top: 0;
  z-index: 100;
  background: #ffffff;
  border-bottom: 1px solid #e2e8f0;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.03);
}
.app-header-inner {
  max-width: 900px;
  margin: 0 auto;
  padding: 12px 15px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}
.brand {
  font-size: 18px;
  font-weight: 700;
  color: #1e293b;
  cursor: pointer;
  user-select: none;
}
.header-right {
  display: flex;
  align-items: center;
  gap: 12px;
}
.header-user {
  font-size: 14px;
  color: #475569;
  font-weight: 500;
}
.new-test-btn {
  padding: 8px 16px;
  font-size: 14px;
  font-weight: 600;
  color: #fff;
  background: #2563eb;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  text-decoration: none;
}
.new-test-btn:hover { background: #1d4ed8; }
.logout-btn {
  padding: 8px 16px;
  font-size: 14px;
  font-weight: 600;
  color: #dc2626;
  background: #fef2f2;
  border: 1px solid #fecaca;
  border-radius: 8px;
  cursor: pointer;
}
.logout-btn:hover { background: #fee2e2; }
.delete-account-btn {
  padding: 8px 14px;
  font-size: 13px;
  font-weight: 500;
  color: #64748b;
  background: transparent;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  cursor: pointer;
}
.delete-account-btn:hover { background: #f8fafc; color: #dc2626; border-color: #fecaca; }
.admin-link {
  padding: 8px 14px;
  font-size: 14px;
  font-weight: 600;
  color: #334155;
  background: #f1f5f9;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  text-decoration: none;
}
.admin-link:hover { background: #e2e8f0; }
</style>
