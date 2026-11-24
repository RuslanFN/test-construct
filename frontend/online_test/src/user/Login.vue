<style lang="css" src="./login.css" />
<script setup>
import { ref, computed } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { login, register } from '../auth';
import CaptchaBox from '../components/CaptchaBox.vue';

const route = useRoute();
const router = useRouter();

const mode = ref('login'); // 'login' | 'register'
const form = ref({
  username: '',
  password: '',
  email: '',
  first_name: '',
  last_name: '',
});
const pdConsent = ref(false);
const error = ref('');
const success = ref('');
const loading = ref(false);
// Мягкая защита на клиенте: после 429 (лимит на сервере) кнопка недоступна
// ещё несколько секунд — заодно отсекает двойные клики и наивные скрипты.
const cooldown = ref(0);
let cooldownTimer = null;






// Капча: при регистрации — всегда; при входе — по требованию сервера.
const captcha = ref({ token: null, answer: '', honeypot: null });
const captchaNeeded = ref(false);
const captchaBox = ref(null);
// На регистрации капча показывается сразу; при входе — до первой неудачи скрыта.
const showCaptcha = computed(() => mode.value === 'register' || captchaNeeded.value);

const buttonDisabled = computed(() => loading.value || cooldown.value > 0);

function onCaptchaChange(v) {
  captcha.value = v;
}

function startCooldown(seconds) {
  cooldown.value = Math.max(1, Math.ceil(seconds || 0));
  if (cooldownTimer) clearInterval(cooldownTimer);
  cooldownTimer = setInterval(() => {
    cooldown.value -= 1;
    if (cooldown.value <= 0) {
      clearInterval(cooldownTimer);
      cooldownTimer = null;
    }
  }, 1000);
}

function switchMode() {
  mode.value = mode.value === 'login' ? 'register' : 'login';
  error.value = '';
  success.value = '';



    captchaNeeded.value = false;
  captcha.value = { token: null, answer: '', honeypot: null };
  // Пересоздаём задачу под новую форму (если блок виден — компонент загрузит сам).
  captchaBox.value?.reset?.();
}

async function submit() {
  error.value = '';
  success.value = '';
  if (mode.value === 'register') {
    if (!pdConsent.value) {
      error.value = 'Необходимо согласие на обработку персональных данных';
      return;
    }
    if ((form.value.password || '').length < 8) {
      error.value = 'Пароль должен содержать не менее 8 символов';
      return;
    }
    if (!form.value.username.trim() || !form.value.email.trim()
        || !form.value.first_name.trim() || !form.value.last_name.trim()) {
      error.value = 'Заполните все обязательные поля';
      return;
    }
  }
  loading.value = true;
  try {
    if (mode.value === 'login') {
      await login(form.value.username, form.value.password, captcha.value);
      const redirect = typeof route.query.redirect === 'string' ? route.query.redirect : '/profile';
      router.push(redirect);
    } else {
      const res = await register({
        username: form.value.username,
        password: form.value.password,
        email: form.value.email,
        pd_consent: pdConsent.value,
                captcha_token: captcha.value.token,
        captcha_answer: captcha.value.answer,
        captcha_honeypot: captcha.value.honeypot,
      });
      // Регистрация больше не логинит: показываем сообщение об ожидании подтверждения





            success.value = res?.message || 'Заявка на регистрацию отправлена. Дождитесь подтверждения администратором.';
      mode.value = 'login';
      form.value.password = '';
      captchaNeeded.value = false;
      captcha.value = { token: null, answer: '', honeypot: null };
    }
  } catch (e) {
    error.value = e.message || 'Ошибка';
    // 429 — серверный лимит: разблокируем кнопку, когда истечёт Retry-After.
    if (e.captchaRequired) {
            captchaNeeded.value = true;
      captcha.value = { token: null, answer: '', honeypot: null };
      // Ждём рендер блока, затем просим новую задачу.
      setTimeout(() => captchaBox.value?.refresh?.(), 0);
    }
  } finally {
    loading.value = false;
  }
}
</script>

<template>
    <div class="login-form">
        <form @submit.prevent="submit">
            <h1>{{ mode === 'login' ? 'Войти' : 'Регистрация' }}</h1>
            <div class="login-field">
                <label for="username">имя пользователя</label>
                <input id="username" v-model="form.username" type="text" name="username" maxlength="30"
                       placeholder="Введите имя пользователя" required />
            </div>
            <template v-if="mode === 'register'">
                <div class="login-field">
                    <label for="email">почта</label>
                    <input id="email" v-model="form.email" type="email" name="email" maxlength="50"
                           placeholder="you@mail.ru" required />
                </div>
                <div class="login-field">
                    <label for="first_name">имя</label>
                    <input id="first_name" v-model="form.first_name" type="text" name="first_name" maxlength="30" required />
                </div>
                <div class="login-field">
                    <label for="last_name">фамилия</label>
                                        <input id="last_name" v-model="form.last_name" type="text" name="last_name" maxlength="30" required />
                </div>
            </template>
            <div class="password-field">
                <label for="password">пароль</label>
                <input v-model="form.password" type="password" id="password" name="password"
                       placeholder="Введите пароль" required />
            </div>
                        <div v-if="mode === 'register'" class="login-consent">
                <label class="consent-label">
                    <input type="checkbox" v-model="pdConsent" />
                    <span>
                        Я согласен на обработку персональных данных в соответствии с
                        <a href="#" @click.prevent>политикой конфиденциальности</a>
                    </span>
                </label>
            </div>
            <CaptchaBox
                v-if="showCaptcha"
                ref="captchaBox"
                @change="onCaptchaChange"
            />
            <p v-if="success" class="login-success">{{ success }}</p>
            <p v-if="error" class="login-error">{{ error }}</p>
            <div class="button-submit">
                <button type="submit" :disabled="buttonDisabled">
                    <template v-if="loading">...</template>
                    <template v-else-if="cooldown > 0">Подождите {{ cooldown }} с</template>
                    <template v-else>{{ mode === 'login' ? 'Войти' : 'Зарегистрироваться' }}</template>
                </button>
            </div>
            <button type="button" class="toggle-mode" @click="switchMode">
                {{ mode === 'login' ? 'Нет аккаунта? Зарегистрироваться' : 'Уже есть аккаунт? Войти' }}
            </button>
        </form>
        </div>
</template>


