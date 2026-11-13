<script setup>
import { ref, onMounted, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { api } from '../api';

const route = useRoute();
const router = useRouter();

const data = ref(null);
const loading = ref(true);
const error = ref('');

// детали попытки: attemptId -> { loading, data, error }
const details = ref({});
const expanded = ref(null); // какой attemptId раскрыт
const exporting = ref(false);

async function exportCsv() {
  exporting.value = true;
  error.value = '';
  try {
    await api.exportAttempts(route.params.id);
  } catch (e) {
    error.value = e.message;
  } finally {
    exporting.value = false;
  }
}

function fmtDate(iso) {
  try {
    return new Date(iso).toLocaleString('ru-RU');
  } catch {
    return iso;
  }
}

function nameOf(a) {
  if (a.participant) {
    const p = a.participant;
    const fio = [p.last_name, p.first_name, p.middle_name].filter(Boolean).join(' ');
    return fio + (p.certificate_number ? ` (№ ${p.certificate_number})` : '');
  }
  return a.guest_name || (a.user_id ? 'Пользователь' : 'Аноним');
}

function typeLabel(t) {
  return { one: 'один ответ', some: 'несколько', match: 'сопоставление', text: 'текст' }[t] || t;
}

async function load() {
  error.value = '';
  try {
    data.value = await api.testAttempts(route.params.id);
  } catch (e) {
    error.value = e.message;
  } finally {
    loading.value = false;
  }
}

async function toggle(attemptId) {
  if (expanded.value === attemptId) {
    expanded.value = null;
    return;
  }
  expanded.value = attemptId;
  if (details.value[attemptId]) return; // уже загружено
  details.value[attemptId] = { loading: true, data: null, error: '' };
  try {
    const d = await api.attemptDetail(route.params.id, attemptId);
    details.value[attemptId] = { loading: false, data: d, error: '' };
  } catch (e) {
    details.value[attemptId] = { loading: false, data: null, error: e.message };
  }
}

function back() {
  router.push({ name: 'profile' });
}

onMounted(load);

// Переход /results/A -> /results/B в той же вкладке: переиспользуем компонент,
// поэтому перезагружаем при смене id.
watch(
  () => route.params.id,
  () => {
    data.value = null;
    details.value = {};
    expanded.value = null;
    load();
  },
);
</script>

<style lang="css" src="./results.css" />

<template>
  <div class="results-page">
    <div class="results-head">
      <button class="back-btn" @click="back">← К профилю</button>
    </div>

    <p v-if="loading">Загрузка…</p>
    <p v-if="error" class="results-error">{{ error }}</p>

    <template v-if="data">
      <div class="results-titlebar">
        <h1 class="results-title">Результаты: {{ data.test_title }}</h1>
        <button
          class="export-btn"
          :disabled="exporting || data.attempts_count === 0"
          @click="exportCsv"
        >

          {{ exporting ? 'Выгрузка…' : '⭳ Выгрузить Excel' }}
        </button>
      </div>

      <div class="results-summary">
        <div class="summary-card">
          <span class="summary-label">Попыток</span>
          <span class="summary-value">{{ data.attempts_count }}</span>
        </div>
        <div class="summary-card">
          <span class="summary-label">Средний результат</span>
          <span class="summary-value">{{ data.average_percent }}%</span>
        </div>
      </div>

      <div class="results-table">
        <table>
          <thead>
            <tr>
              <th></th>
              <th>Кто прошёл</th>
              <th>Результат</th>
              <th>Процент</th>
              <th>Дата</th>
            </tr>
          </thead>
          <tbody>
            <template v-for="a in data.attempts" :key="a.id">
              <tr class="clickable-row" @click="toggle(a.id)">
                <td class="caret">{{ expanded === a.id ? '▾' : '▸' }}</td>
                <td>{{ nameOf(a) }}</td>
                <td>{{ a.score }} / {{ a.total }}</td>
                <td>
                  <span class="pct" :class="a.percent >= 60 ? 'pct-pass' : 'pct-fail'">{{ a.percent }}%</span>
                </td>
                <td>{{ fmtDate(a.created_at) }}</td>
              </tr>
              <tr v-if="expanded === a.id" class="detail-row">
                <td colspan="5">
                  <div class="detail-box">
                    <p v-if="details[a.id]?.loading">Загрузка ответов…</p>
                    <p v-else-if="details[a.id]?.error" class="results-error">{{ details[a.id].error }}</p>
                    <div v-else-if="details[a.id]?.data" class="detail-list">
                      <div
                        v-for="(q, qi) in details[a.id].data.questions"
                        :key="q.question_id"
                        class="detail-item"
                        :class="q.is_correct ? 'ok' : 'bad'"
                      >
                        <div class="detail-qtext">
                          <span class="detail-qnum">{{ qi + 1 }}.</span>
                          {{ q.text || '—' }}
                          <span class="detail-type">{{ typeLabel(q.type) }}</span>
                          <span class="detail-mark">{{ q.is_correct ? '✓ верно' : '✗ неверно' }}</span>
                        </div>
                        <div class="detail-answers">
                          <div class="detail-line">
                            <span class="detail-label">Ответ:</span>
                            <span class="detail-given">
                              {{ q.given.length ? q.given.join(', ') : '— (нет ответа)' }}
                            </span>
                          </div>
                          <div v-if="!q.is_correct" class="detail-line">
                            <span class="detail-label">Правильно:</span>
                            <span class="detail-correct">{{ q.correct.join(', ') }}</span>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                </td>
              </tr>
            </template>
            <tr v-if="data.attempts.length === 0">
              <td colspan="5" class="empty-row">Пока никто не проходил этот тест</td>
            </tr>
          </tbody>
        </table>
      </div>
    </template>
  </div>
</template>
