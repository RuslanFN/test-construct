<script setup>
import { ref } from 'vue';
import { api } from '../api';

// Арифметическая капча «я не робот»: пример СЛОВАМИ, ответ ЦИФРАМИ.
// Задача запрашивается у сервера, ответ проверяется на сервере
// (подписанный одноразовый токен + honeypot).
const props = defineProps({
  label: { type: String, default: 'Проверка «я не робот»' },
});
const emit = defineEmits(['change']); // отдаёт { token, answer, honeypot }

const question = ref('');
const token = ref('');
const answer = ref('');
const honeypot = ref(''); // скрытое поле-ловушка: человек его не видит
const loading = ref(false);
const loaded = ref(false);
const error = ref('');

function notify() {
  // Поле type="number" даёт число — приводим к строке (контракт API: строка).
  emit('change', {
    token: token.value || null,

    answer: answer.value === '' || answer.value === null ? '' : String(answer.value),
    honeypot: honeypot.value || null,
  });
}

async function load() {
  loading.value = true;
  loaded.value = false;
  error.value = '';
  answer.value = '';
  try {
    const data = await api.getCaptcha();
    question.value = data.question;
    token.value = data.token;
    loaded.value = true;
  } catch (e) {
    error.value = e.message || 'Не удалось загрузить задачу';
  } finally {
    loading.value = false;
    notify();
  }
}

// После неудачной отправки задача израсходована — обновляем.
defineExpose({ refresh: load, reset: load });
</script>

<template>
  <div class="captcha">
    <label class="captcha-label">{{ label }}</label>
    <div class="captcha-row">
      <!-- Задача запрашивается только по нажатию (в конце теста), а не при загрузке -->
      <button v-if="!loaded && !loading" type="button" class="captcha-start" @click="load">
        Показать пример
      </button>
      <span v-if="loading" class="captcha-q">…</span>
      <template v-else-if="loaded">
        <span class="captcha-q">Сколько будет: {{ question }}?</span>
        <input
        v-model="answer"
        type="number"
        inputmode="numeric"
        class="captcha-input"
        placeholder="Ответ"
        @input="notify"
      />
        <button type="button" class="captcha-refresh" title="Другой пример"
              :disabled="loading" @click="load">⟳</button>
</template>
    </div>
    <p v-if="loaded" class="captcha-hint">Введите ответ цифрами.</p>
    <!-- Ловушка для ботов: визуально скрыта, человек её не видит и не заполняет -->
    <div class="captcha-hp" aria-hidden="true">
      <label for="hp-email">E-mail</label>
      <input
        id="hp-email"
        v-model="honeypot"
        type="text"
        name="email"
        tabindex="-1"
        autocomplete="off"
        @input="notify"
      />
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
  color: #334155;
}
.captcha-row {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}
.captcha-q {
  font-size: 15px;
  color: #0f172a;
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
.captcha-start {
  padding: 10px 16px;
  font-size: 14px;
  font-weight: 600;
  color: #1f6feb;
  background: #eef4ff;
  border: 1px solid #c7dbff;
  border-radius: 8px;
  cursor: pointer;
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
.captcha-hint {
  margin: 0;
  font-size: 12px;
  color: #64748b;
}
/* Honeypot: уводим за пределы экрана, но оставляем в DOM (боты-парсеры
   заполняют такие поля, люди — нет). Не display:none — часть ботов пропустит. */
.captcha-hp {
  position: absolute;
  left: -9999px;
  top: -9999px;
  height: 0;
  overflow: hidden;
}
.captcha-error {
  margin: 0;
  font-size: 13px;
  color: #b91c1c;
}
</style>

