<style lang="css" src="./profile.css" />
<script setup>
import { ref, computed, onMounted, watch } from 'vue';
import { useRouter } from 'vue-router';
import { api } from '../api';
import { authState } from '../auth';
import Pagination from '../components/Pagination.vue';

const router = useRouter();

const tests = ref([]);
const loading = ref(false);
const error = ref('');

const user = authState.user;

// Пагинация таблицы тестов
const page = ref(1);
const pageSize = 10;
const pageCount = computed(() => Math.max(1, Math.ceil(tests.value.length / pageSize)));
const pagedTests = computed(() => {
  const start = (page.value - 1) * pageSize;
  return tests.value.slice(start, start + pageSize);
});
// если после обновления/удаления текущая страница стала пустой — вернёмся назад
watch(pageCount, (c) => { if (page.value > c) page.value = c; });

function publicLink(token) {
  return `${window.location.origin}/#/take/${token}`;
}

async function loadTests() {
  loading.value = true;
  error.value = '';
  try {
    tests.value = await api.myTests();
  } catch (e) {
    error.value = e.message;
  } finally {
    loading.value = false;
  }
}

async function togglePublish(test) {
  try {
    if (test.status === 'published') await api.unpublishTest(test.id);
    else await api.publishTest(test.id);
    await loadTests();
  } catch (e) {
    error.value = e.message;
  }
}

async function removeTest(test) {
  if (!confirm(`Удалить тест «${test.title}»?`)) return;
  try {
    await api.deleteTest(test.id);
    await loadTests();
  } catch (e) {
    error.value = e.message;
  }
}

function copyLink(test) {
  navigator.clipboard?.writeText(publicLink(test.public_token));
}

function openEditor(id) {
  router.push({ name: 'editor', params: { id } });
}

function openResults(id) {
  router.push({ name: 'results', params: { id } });
}

onMounted(loadTests);

defineExpose({ loadTests });
</script>

<template>
  <div class="profile-page">
    <div class="profile-info" v-if="user">
        <div class="profile-item">
            <span class="profile-label">имя пользователя</span>
            <span class="profile-value">{{ user.username }}</span>
        </div>
        <div class="profile-item">
            <span class="profile-label">Фамилия</span>
            <span class="profile-value">{{ user.last_name }}</span>
        </div>
        <div class="profile-item">
            <span class="profile-label">Имя</span>
            <span class="profile-value">{{ user.first_name }}</span>
        </div>
        <div class="profile-item">
            <span class="profile-label">Отчество</span>
            <span class="profile-value">{{ user.middle_name || '—' }}</span>
        </div>
        <div class="profile-item">
            <span class="profile-label">Почта</span>
            <span class="profile-value">{{ user.email }}</span>
        </div>
        <div class="profile-item">
            <span class="profile-label">Телефон</span>
            <span class="profile-value">{{ user.phone || '—' }}</span>
        </div>
    </div>
    <div class="profile-actions-top">
        <h2>Мои тесты</h2>
    </div>
        <p v-if="error" class="profile-error">{{ error }}</p>
    <div class="tests-table">
        <table>
            <thead>
                <tr>
                    <th>Наименование теста</th>
                    <th>статус</th>
                    <th>Действия</th>
                </tr>
            </thead>
            <tbody>
                <tr v-if="loading">
                    <td colspan="3" class="empty-row">Загрузка…</td>
                </tr>
                <tr v-for="test in pagedTests" :key="test.id">
                    <td>{{ test.title }} <span class="qcount">({{ test.questions_count }} вопр.)</span></td>





                                        <td>
                        <span class="status" :class="test.status === 'published' ? 'status--published' : 'status--draft'">
                            {{ test.status === 'published' ? 'опубликован' : 'черновик' }}
                        </span>
                    </td>
                    <td>
                        <button @click="togglePublish(test)">
                            {{ test.status === 'published' ? 'снять с публикации' : 'опубликовать' }}
                        </button>
                                                <button @click="openResults(test.id)">результаты</button>
                        <button v-if="test.status === 'published'" @click="copyLink(test)">копировать ссылку</button>
                        <button
                            :disabled="test.status === 'published'"
                            :title="test.status === 'published' ? 'Опубликованный тест редактировать нельзя — сначала снимите с публикации' : 'Редактировать тест'"
                            @click="openEditor(test.id)"
                        >редактировать</button>
                        <button @click="removeTest(test)">удалить</button>
                    </td>
                </tr>
                <tr v-if="!loading && tests.length === 0">
                    <td colspan="3" class="empty-row">Тестов пока нет</td>
                </tr>
            </tbody>
        </table>
        <Pagination v-model:page="page" :total="tests.length" :page-size="pageSize" />
    </div>
  </div>
</template>