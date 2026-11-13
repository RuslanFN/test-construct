упо<script setup>
import { ref, onMounted, computed, watch } from 'vue';
import { api } from '../api';

const props = defineProps({ token: { type: String, required: true } });

const test = ref(null);
const loading = ref(true);
const error = ref('');
const result = ref(null);
const submitting = ref(false);

// данные участника (без аккаунта)
const participant = ref({
  last_name: '',
  first_name: '',
  middle_name: '',
  certificate_number: '',
});

// ответы: по questionId
const answers = ref({}); // { [qid]: { selected: [], matches: {} } }

function ensureAnswer(qid) {
  if (!answers.value[qid]) answers.value[qid] = { selected: [], matches: {} };
  return answers.value[qid];
}

function toggleSingle(q, answerId) {
  answers.value[q.id] = { selected: [answerId], matches: {} };
}

function toggleMultiple(q, answerId) {
  const a = ensureAnswer(q.id);
  const idx = a.selected.indexOf(answerId);
  if (idx >= 0) a.selected.splice(idx, 1);
  else a.selected.push(answerId);
}

function setText(q, value) {
  answers.value[q.id] = { selected: [value], matches: {} };
}

// Порядок правых вариантов для вопроса-сопоставления: массив rightIdx,
// где позиция = leftIdx. Правильно, когда на позиции i стоит правый вариант i.
const matchOrder = ref({}); // { [qid]: number[] }

function ensureOrder(q) {
  if (!matchOrder.value[q.id]) {
    // исходный порядок: позиция i = правый вариант i (то есть «правильный»)
    matchOrder.value[q.id] = q.pairs_right.map((_, i) => i);
  }
  return matchOrder.value[q.id];
}

function moveMatch(q, pos, dir) {
  const order = ensureOrder(q);
  const target = pos + dir;
  if (target < 0 || target >= order.length) return;
  const tmp = order[pos];
  order[pos] = order[target];
  order[target] = tmp;
  // sync answers: на позиции i теперь правый order[i]
  syncMatches(q);
}

function shuffleMatch(q) {
  const order = ensureOrder(q);
  // перемешиваем (Фишер–Йетс)
  for (let i = order.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [order[i], order[j]] = [order[j], order[i]];
  }
  // не оставляем случайно уже правильный порядок
  const n = order.length;
  let correct = true;
  for (let i = 0; i < n; i++) {
    if (order[i] !== i) { correct = false; break; }
  }
  if (correct && n > 1) {
    [order[0], order[1]] = [order[1], order[0]];
  }
  syncMatches(q);
}

// Перекладываем порядок в формат ответа: пары (leftIdx -> rightIdx).
function syncMatches(q) {
  const order = ensureOrder(q);
  const a = ensureAnswer(q.id);
  a.matches = {};
  order.forEach((rightIdx, leftIdx) => {
    a.matches[leftIdx] = rightIdx;
  });
}

async function load() {
  loading.value = true;
  error.value = '';
  try {
    test.value = await api.getPublicTest(props.token);
    // для вопросов-сопоставлений сразу перемешиваем правые варианты,
    // чтобы порядок по умолчанию не был правильным, и синхронизируем ответ
    matchOrder.value = {};
    for (const q of test.value.questions) {
      if (q.type === 'match') {
        ensureOrder(q);
        shuffleMatch(q);
      }
    }
  } catch (e) {
    error.value = e.message;
  } finally {
    loading.value = false;
  }
}

const canSubmit = computed(() => {
  if (!test.value || test.value.questions.length === 0) return false;
  // данные участника обязательны (отчество — нет)
  const p = participant.value;
  if (!p.last_name.trim() || !p.first_name.trim()) return false;
  if (!/^\d{10}$/.test(p.certificate_number.trim())) return false;
  for (const q of test.value.questions) {
    if (!q.required) continue;
    const a = answers.value[q.id];
    let ok = false;
    if (a) {
      if (q.type === 'match') {
        // все правые варианты расставляются по позициям — считаем отвеченным,
        // если варианты вообще есть
        ok = q.pairs_left.length > 0;
      } else {
        ok = a.selected.some((v) => (typeof v === 'string' ? v.trim() !== '' : true));
      }
    }
    if (!ok) return false;
  }
  return true;
});

async function submit() {
  submitting.value = true;
  error.value = '';
  try {
    const payload = {
      participant: {
        last_name: participant.value.last_name.trim(),
        first_name: participant.value.first_name.trim(),
        middle_name: participant.value.middle_name.trim() || null,
        certificate_number: participant.value.certificate_number.trim(),
      },
      answers: Object.entries(answers.value).map(([qid, a]) => ({
        question_id: qid,
        selected: a.selected,
        matches: Object.entries(a.matches).map(([l, r]) => [Number(l), Number(r)]),
      })),
    };
    result.value = await api.submitAttempt(props.token, payload);
  } catch (e) {
    error.value = e.message;
  } finally {
    submitting.value = false;
  }
}

onMounted(load);

// Если меняется token (переход /take/OLD -> /take/NEW в той же вкладке),
// компонент переиспользуется — нужно сбросить состояние и загрузить заново.
watch(
  () => props.token,
  () => {
    test.value = null;
    result.value = null;
    answers.value = {};

    participant.value = { last_name: '', first_name: '', middle_name: '', certificate_number: '' };
    error.value = '';
    load();
  },
);
</script>

<style lang="css" src="./take.css" />

<template>
  <div class="take-page">
    <p v-if="loading">Загрузка…</p>
    <p v-if="error" class="take-error">{{ error }}</p>

    <div v-if="result" class="take-result">
      <h1>Результат</h1>
      <div class="score-circle" :class="result.percent >= 60 ? 'score-pass' : 'score-fail'">
        {{ result.percent }}%
      </div>
      <p class="score-text">Правильных ответов: {{ result.score }} из {{ result.total }}</p>
      <ul class="result-list">
        <li v-for="(r, i) in result.results" :key="r.question_id" :class="r.is_correct ? 'ok' : 'bad'">
          Вопрос {{ i + 1 }}: {{ r.is_correct ? 'верно' : 'неверно' }}
        </li>
      </ul>
    </div>

    <template v-else-if="test">
      <div class="take-header">
        <h1>{{ test.title }}</h1>
        <p v-if="test.description" class="take-desc">{{ test.description }}</p>
      </div>

      <div class="take-participant">
        <p class="take-participant-title">Данные участника</p>
        <div class="take-participant-grid">
          <label class="take-field">
            <span>Фамилия <span class="take-required">*</span></span>
            <input type="text" v-model="participant.last_name" placeholder="Иванов" />
          </label>
          <label class="take-field">
            <span>Имя <span class="take-required">*</span></span>
            <input type="text" v-model="participant.first_name" placeholder="Иван" />
          </label>
          <label class="take-field">
            <span>Отчество</span>
            <input type="text" v-model="participant.middle_name" placeholder="Иванович" />
          </label>
          <label class="take-field">

            <span>Номер сертификата ПФДО <span class="take-required">*</span></span>
            <input
              type="text"
              v-model="participant.certificate_number"
              inputmode="numeric"
              maxlength="10"
              placeholder="10 цифр"
              @input="participant.certificate_number = participant.certificate_number.replace(/\D/g, '').slice(0, 10)"
            />
          </label>
        </div>
      </div>

      <div class="take-question" v-for="(q, qi) in test.questions" :key="q.id">
        <div class="take-qtext">
          <span class="take-qnum">{{ qi + 1 }}.</span>
          {{ q.text || (q.type === 'match' ? 'Сопоставьте значения:' : 'Вопрос ' + (qi + 1)) }}
          <span v-if="q.required" class="take-required" title="Обязательный вопрос">*</span>
        </div>

        <!-- один правильный -->
        <div v-if="q.type === 'one'" class="take-options">
          <label v-for="a in q.answers" :key="a.id" class="take-option">
            <input type="radio" :name="'q-' + q.id" @change="toggleSingle(q, a.id)" />
            <span>{{ a.text }}</span>
          </label>
        </div>

        <!-- несколько правильных -->
        <div v-else-if="q.type === 'some'" class="take-options">
          <label v-for="a in q.answers" :key="a.id" class="take-option">
            <input type="checkbox" @change="toggleMultiple(q, a.id)" />
            <span>{{ a.text }}</span>
          </label>
        </div>

        <!-- текст -->
        <div v-else-if="q.type === 'text'" class="take-options">
          <input class="take-text-input" type="text" placeholder="Ваш ответ"
                 @input="setText(q, $event.target.value)" />
        </div>

        <!-- сопоставление (перестановка стрелками) -->
        <div v-else-if="q.type === 'match'" class="take-match">
          <p class="take-match-hint">
            Расставьте правые значения в правильном порядке кнопками ▲ ▼
          </p>
          <div class="take-match-row" v-for="(left, pos) in q.pairs_left" :key="pos">
            <div class="take-match-left">
              <span class="take-match-pos">{{ pos + 1 }}.</span>
              {{ left }}
            </div>
            <div class="take-match-right">
              <span class="take-match-value">{{ q.pairs_right[matchOrder[q.id][pos]] }}</span>
              <div class="take-match-buttons">
                <button type="button" class="take-arrow" :disabled="pos === 0"
                        title="Выше" @click="moveMatch(q, pos, -1)">▲</button>
                <button type="button" class="take-arrow" :disabled="pos === q.pairs_left.length - 1"
                        title="Ниже" @click="moveMatch(q, pos, 1)">▼</button>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div class="take-submit">
        <button :disabled="!canSubmit || submitting" @click="submit">
          {{ submitting ? 'Проверка…' : 'Завершить тест' }}
        </button>
      </div>
      <p class="take-hint"><span class="take-required">*</span> — обязательный вопрос</p>
    </template>
  </div>
</template>
