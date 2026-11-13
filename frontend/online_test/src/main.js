import { createApp } from 'vue';
import './style.css';
import App from './App.vue';
import router from './router';
import { restoreSession } from './auth';

const app = createApp(App);

// Восстанавливаем сессию (по HttpOnly-куке) до первого рендера,
// чтобы не было "мелькания" логина.
restoreSession().finally(() => {
  app.use(router);
  app.mount('#app');
});
