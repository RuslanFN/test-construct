<style lang="css" src="./login.css" />
<script setup>
import { ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { login, register } from '../auth';

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
      await login(form.value.username, form.value.password);
      const redirect = typeof route.query.redirect === 'string' ? route.query.redirect : '/profile';
      router.push(redirect);
    } else {
      const res = await register({
        username: form.value.username,
        password: form.value.password,
        email: form.value.email,
        first_name: form.value.first_name,
        last_name: form.value.last_name,
        pd_consent: pdConsent.value,
      });
      // Регистрация больше не логинит: показываем сообщение об ожидании подтверждения
      success.value = res?.message || 'Заявка на регистрацию отправлена. Дождитесь подтверждения администратором.';
      mode.value = 'login';
      form.value.password = '';
    }
  } catch (e) {
    error.value = e.message || 'Ошибка';
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
            <p v-if="success" class="login-success">{{ success }}</p>
            <p v-if="error" class="login-error">{{ error }}</p>
            <div class="button-submit">
                <button type="submit" :disabled="loading">
                    {{ loading ? '...' : (mode === 'login' ? 'Войти' : 'Зарегистрироваться') }}
                </button>
            </div>
            <button type="button" class="toggle-mode" @click="mode = mode === 'login' ? 'register' : 'login'">
                {{ mode === 'login' ? 'Нет аккаунта? Зарегистрироваться' : 'Уже есть аккаунт? Войти' }}
            </button>
        </form>
        </div>
</template>


