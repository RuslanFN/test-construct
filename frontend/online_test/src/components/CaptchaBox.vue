<script setup>
import { ref, onMounted } from 'vue';
import { api } from '../api';

// Арифметическая капча «я не робот». Задача запрашивается у сервера,
// ответ проверяется на сервере (подписанный одноразовый токен).
const props = defineProps({
  label: { type: String, default: 'Проверка «я не робот»' },
});
const emit = defineEmits(['change']); // отдаёт { token, answer } родителю

const question = ref('');
const token = ref('');
const answer = ref('');
const loading = ref(false);
const error = ref('');

function notify() {
  emit('change', { token: token.value || null, answer: answer.value });
}

async function load() {
  loading.value = true;
  error.value = '';
  answer.value = '';
  try {
    const data = await api.getCaptcha();
    question.value = data.question;
    token.value = data.token;
  } catch (e) {
    error.value = e.message || 'Не удалось загрузить задачу';
  } finally {
    loading.value = false;
    notify();
  }
}

onMounted(load);

// После неудачной отправки задача израсходована — обновляем.
defineExpose({ refresh: load, reset: load });
</script>

<template>
  <div class="captcha">
    <label class="captcha-label">{{ label }}</label>
    <div class="captcha-row">
      <span v-if="loading" class="captcha-q">…</span>
      <span v-else class="captcha-q">Сколько будет {{ question }} ?</span>
      <input
        v-model="answer"
        type="number"
        inputmode="numeric"
        class="captcha-input"
        placeholder="Ответ"
        @input="notify"
      />
      <button type="button" class="captcha-refresh" title="Другая задача"
              :disabled="loading" @click="load">⟳</button>
    </div>
    <p v-if="error" class="captcha-error">{{ error }}</p>
  </div>
</template>

<style scoped>
.captcha {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.captcha-label {
  font-size: 14px;
  font-weight: 600;
  color: #334155;
}
.captcha-row {
  display: flex;
  align-items: center;
  gap: 10px;
}
.captcha-q {
  font-size: 15px;
  color: #0f172a;
  white-space: nowrap;
}
.captcha-input {
  width: 90px;
  padding: 10px 12px;
  font-size: 14px;
  color: #0f172a;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  outline: none;
}
.captcha-input:focus {
  border-color: #1f6feb;
  box-shadow: 0 0 0 3px rgba(31, 111, 235, 0.15);
}
.captcha-refresh {
  padding: 6px 10px;
  font-size: 16px;
  line-height: 1;
  color: #1f6feb;
  background: #eef4ff;
  border: 1px solid #c7dbff;
  border-radius: 8px;
  cursor: pointer;
}
.captcha-refresh:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.captcha-error {
  margin: 0;
  font-size: 13px;
  color: #b91c1c;
}
</style>
