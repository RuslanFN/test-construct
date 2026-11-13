<script setup>
import { ref, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { api } from '../api';

const router = useRouter();

const tab = ref('tests'); // 'tests' | 'users'

// ---- Тесты ----
const tests = ref([]);
const loadingTests = ref(false);
const testsError = ref('');
const query = ref('');
const statusFilter = ref('');

async function loadTests() {
  loadingTests.value = true;
  testsError.value = '';
  try {
    tests.value = await api.adminTests({ q: query.value.trim(), status: statusFilter.value });
  } catch (e) {
    testsError.value = e.message;
  } finally {
    loadingTests.value = false;
  }
}

let searchTimer = null;
function onSearchInput() {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(loadTests, 300);
}

async function toggleTest(t) {
  try {
    if (t.status === 'published') await api.unpublishTest(t.id);
    else await api.publishTest(t.id);
    await loadTests();
  } catch (e) {
    alert(e.message);
  }
}

async function deleteTest(t) {
  if (!confirm(`Удалить тест «${t.title}» и все его результаты? Действие необратимо.`)) return;
  try {
    await api.deleteTest(t.id);
    await loadTests();
  } catch (e) {
    alert(e.message);
  }
}

// ---- Пользователи ----
const users = ref([]);
const loadingUsers = ref(false);
const usersError = ref('');

async function loadUsers() {
  loadingUsers.value = true;
  usersError.value = '';
  try {
    users.value = await api.adminUsers();
  } catch (e) {
    usersError.value = e.message;
  } finally {
    loadingUsers.value = false;
  }
}

async function toggleUser(u) {
  try {
    await api.adminSetUserActive(u.id, !u.is_active);
    await loadUsers();
  } catch (e) {
    alert(e.message);
  }
}

async function approveUser(u) {
  try {
    await api.adminSetApproval(u.id, 'approved');
    await loadUsers();
  } catch (e) {
    alert(e.message);
  }
}

async function rejectUser(u) {
  if (!confirm(`Отклонить заявку «${u.username}»?`)) return;
  try {
    await api.adminSetApproval(u.id, 'rejected');
    await loadUsers();
  } catch (e) {
    alert(e.message);
  }
}

async function deleteUser(u) {
  if (!confirm(`Удалить учётную запись «${u.username}»? Действие необратимо.`)) return;
  try {
    await api.adminDeleteUser(u.id);
    await loadUsers();
  } catch (e) {
    alert(e.message);
  }
}

function fmtDate(iso) {
  try { return new Date(iso).toLocaleString('ru-RU'); } catch { return iso; }
}

function statusLabel(s) {
  return s === 'published' ? 'Опубликован' : 'Черновик';
}

function approvalLabel(u) {
  if (u.approval_status === 'pending') return 'Ожидает подтверждения';
  if (u.approval_status === 'rejected') return 'Отклонена';
  return u.is_active ? 'Активна' : 'Заблокирована';
}

function approvalClass(u) {
  if (u.approval_status === 'pending') return 'badge-pending';
  if (u.approval_status === 'rejected') return 'badge-rejected';
  return u.is_active ? 'badge-pub' : 'badge-draft';
}

onMounted(() => {
  loadTests();
  loadUsers();
});
</script>

<style lang="css" src="./admin.css" />

<template>
  <div class="admin-page">
    <h1 class="admin-title">Админ-панель</h1>

    <div class="admin-tabs">
      <button :class="{ active: tab === 'tests' }" @click="tab = 'tests'">Тесты</button>
      <button :class="{ active: tab === 'users' }" @click="tab = 'users'">Пользователи</button>
    </div>

    <!-- ===== ТЕСТЫ ===== -->
    <section v-if="tab === 'tests'" class="admin-section">
      <div class="admin-toolbar">
        <input
          class="admin-search"
          v-model="query"
          @input="onSearchInput"
          placeholder="Поиск: название или публичный токен…"
        />
        <select v-model="statusFilter" @change="loadTests" class="admin-select">
          <option value="">Все статусы</option>
          <option value="published">Опубликованные</option>
          <option value="draft">Черновики</option>
        </select>
        <button class="admin-btn" @click="loadTests">Обновить</button>
      </div>

      <p v-if="loadingTests">Загрузка…</p>
      <p v-if="testsError" class="admin-error">{{ testsError }}</p>

      <table v-if="!loadingTests && tests.length" class="admin-table">
        <thead>
          <tr>
            <th>Название</th>
            <th>Автор</th>
            <th>Статус</th>
            <th>Вопросов</th>
            <th>Попыток</th>
            <th>Токен</th>
            <th>Действия</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="t in tests" :key="t.id">
            <td class="cell-title">{{ t.title }}</td>
            <td>{{ t.author_username || '—' }}</td>
            <td>
              <span class="badge" :class="t.status === 'published' ? 'badge-pub' : 'badge-draft'">
                {{ statusLabel(t.status) }}
              </span>
            </td>
            <td>{{ t.questions_count }}</td>
            <td>{{ t.attempts_count }}</td>
            <td class="cell-token">{{ t.public_token || '—' }}</td>
            <td class="cell-actions">
              <button class="link-btn" @click="router.push({ name: 'results', params: { id: t.id } })">Результаты</button>
              <button class="link-btn" @click="toggleTest(t)">
                {{ t.status === 'published' ? 'Скрыть' : 'Опубликовать' }}
              </button>
              <button class="link-btn danger" @click="deleteTest(t)">Удалить</button>
            </td>
          </tr>
        </tbody>
      </table>
      <p v-else-if="!loadingTests" class="admin-empty">Тесты не найдены</p>
    </section>

    <!-- ===== ПОЛЬЗОВАТЕЛИ ===== -->
    <section v-if="tab === 'users'" class="admin-section">
      <div class="admin-toolbar">
        <button class="admin-btn" @click="loadUsers">Обновить</button>
      </div>

      <p v-if="loadingUsers">Загрузка…</p>
      <p v-if="usersError" class="admin-error">{{ usersError }}</p>

      <table v-if="!loadingUsers && users.length" class="admin-table">
        <thead>
          <tr>
            <th>Логин</th>
            <th>ФИО</th>
            <th>Email</th>
            <th>Роль</th>
            <th>Статус</th>
            <th>Создан</th>
            <th>Действия</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="u in users" :key="u.id">
            <td>{{ u.username }} <span v-if="u.is_service" class="badge badge-service">служебная</span></td>
            <td>{{ [u.last_name, u.first_name, u.middle_name].filter(Boolean).join(' ') || '—' }}</td>
            <td>{{ u.email || '—' }}</td>
            <td>{{ u.role === 'admin' ? 'Админ' : 'Методист' }}</td>
            <td>
              <span class="badge" :class="approvalClass(u)">
                {{ approvalLabel(u) }}
              </span>
            </td>
            <td>{{ fmtDate(u.created_at) }}</td>
            <td class="cell-actions">
              <template v-if="!u.is_service">
                <template v-if="u.approval_status === 'pending'">
                  <button class="link-btn" @click="approveUser(u)">Одобрить</button>
                  <button class="link-btn danger" @click="rejectUser(u)">Отклонить</button>
                </template>
                <template v-else>
                  <button class="link-btn" @click="toggleUser(u)">
                    {{ u.is_active ? 'Заблокировать' : 'Разблокировать' }}
                  </button>
                  <button class="link-btn danger" @click="deleteUser(u)">Удалить</button>
                </template>
              </template>
              <span v-else class="cell-muted">—</span>
            </td>
          </tr>
        </tbody>
      </table>
      <p v-else-if="!loadingUsers" class="admin-empty">Нет пользователей</p>
    </section>
  </div>
</template>
