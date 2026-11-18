<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import {
    type QuestionItem,
    type OneCorrect,
    type SomeCorrect,
    type MatchAnswers,
    type TextAnswers,
    QuestionType,
} from './schemas.ts';
import OneCorrectComponent from './OneCorrect.vue';
import SomeCorrectComponent from './SomeCorrect.vue';
import MatchAnswersComponent from './MatchAnswers.vue';
import TextAnswerComponent from './TextAnswer.vue';
import ImageUploadComponent from './ImageUpload.vue';
import { api } from '../api';

const route = useRoute();
const router = useRouter();

const questions = ref<QuestionItem[]>([]);
const currentSelected = ref<QuestionType>(QuestionType.One);
const title = ref('');
const description = ref('');
const status = ref<'draft' | 'published'>('draft');
const editingId = ref<string | null>(null);
const updatedAt = ref<string | null>(null); // версия теста для защиты от затирания
const conflict = ref(false);
const saving = ref(false);
const error = ref('');
const message = ref('');

// Опубликованный тест редактировать нельзя. Статус берём с сервера (loadTest),
// поэтому открытая «просроченная» страница тоже не даст сохранить правки.
const isPublished = computed(() => status.value === 'published');

let localSeq = 1;
function nextLocalId() {
    return localSeq++;
}

// Сбрасываем состояние формы и загружаем тест по id из маршрута.
function initFromRoute() {
    const routeId = route.params.id as string;
    editingId.value = routeId && routeId !== 'new' ? routeId : null;
    questions.value = [];
    title.value = '';
    description.value = '';
    status.value = 'draft';
    error.value = '';
    message.value = '';
    localSeq = 1;
    loadTest();
}

function addQuestionItem() {
    const id = nextLocalId();
    questions.value.push({
        id,
        question: { questionId: id, type: currentSelected.value, text: '', required: false, imageIds: [] },
        answers: [],
    });
}

function removeQuestion(id: number) {
    const idx = questions.value.findIndex(q => q.id === id);
    if (idx >= 0) questions.value.splice(idx, 1);
}

// ---- фронтенд -> бэкенд ----
// ВАЖНО: id вопросов/ответов/пар переиспользуем, если они пришли с сервера.
// Иначе при каждом сохранении генерировался бы новый UUID, и старые попытки
// прохождения теряли бы связь «ответ -> вариант» (в них хранятся эти id).
function uid(uuid?: string): string {
    return uuid || crypto.randomUUID();
}

function toBackendQuestion(item: QuestionItem) {
    const type = item.question.type;
    const required = !!item.question.required;
    const questionId = uid(typeof item.question.questionId === 'string' ? item.question.questionId : undefined);
    const image_ids = [...(item.question.imageIds || [])];

    if (type === QuestionType.Match) {
        const pairs = (item.answers as MatchAnswers[]).map((a) => ({
            id: uid(a.uuid),
            left: a.text1,
            right: a.text2,
        }));
        return { id: questionId, type: 'match', text: item.question.text, required, answers: [], pairs, image_ids };
    }
    const answers = (item.answers as any[]).map((a) => ({
        id: uid(a.uuid),
        text: a.text,
        is_correct: type === QuestionType.Text ? true : !!a.isCorrect,
    }));
    const mapType = type === QuestionType.One ? 'one' : type === QuestionType.Some ? 'some' : 'text';
    return { id: questionId, type: mapType, text: item.question.text, required, answers, pairs: [], image_ids };
}

// ---- бэкенд -> фронтенд ----
function fromBackendQuestion(q: any): QuestionItem {
    const id = nextLocalId();
    const item: QuestionItem = {
        id,
                question: {
            // сохраняем настоящий UUID вопроса, чтобы вернуть его при сохранении
            questionId: q.id,
            type: q.type as QuestionType,
            text: q.text ?? '',
            required: !!q.required,
            imageIds: [...(q.image_ids || [])],
        },
        answers: [],
    };
    if (q.type === 'match') {
        item.answers = (q.pairs || []).map((p: any, i: number) => ({
            id: i + 1,
            questionId: id,
            uuid: p.id,          // настоящий UUID пары
            text1: p.left,
            text2: p.right,
        }));
    } else {
        item.answers = (q.answers || []).map((a: any, i: number) => ({
            id: i + 1,
            questionId: id,
            uuid: a.id,          // настоящий UUID варианта
            text: a.text,
            isCorrect: a.is_correct,
        }));
    }
    return item;
}

async function loadTest() {
    if (!editingId.value) return;
    try {
        const t = await api.getTest(editingId.value);
        title.value = t.title;
        description.value = t.description ?? '';
        status.value = t.status;
        updatedAt.value = t.updated_at ?? null;
        questions.value = (t.questions || []).map(fromBackendQuestion);
    } catch (e: any) {
        error.value = e.message;
    }
}

async function save(publish = false) {
    error.value = '';
    message.value = '';
    conflict.value = false;
    // Защита на клиенте: опубликованный тест не редактируется.
    if (isPublished.value) {
        error.value = 'Тест опубликован — редактирование недоступно. Снимите его с публикации в профиле.';
        return;
    }
    saving.value = true;
    try {
        const payload: any = {
            title: title.value,
            description: description.value || null,
            status: publish ? 'published' : status.value,
            questions: questions.value.map(toBackendQuestion),
        };
        if (editingId.value && updatedAt.value) {
            payload.expected_updated_at = updatedAt.value;
        }
        let saved;
        if (editingId.value) {
            saved = await api.updateTest(editingId.value, payload);
        } else {
            saved = await api.saveTest(payload);
            editingId.value = saved.id;
            // фиксируем id в URL, чтобы сохранение дальше шло в тот же тест
            router.replace({ name: 'editor', params: { id: saved.id } });
        }
        status.value = saved.status;
        updatedAt.value = saved.updated_at ?? updatedAt.value;
        message.value = 'Сохранено';
        } catch (e: any) {
        if (e.status === 409 && /опубликован/i.test(e.message || '')) {
            error.value = e.message;
            conflict.value = false;
        } else if (e.status === 409) {
            conflict.value = true;
        } else {
            error.value = e.message;
        }
    } finally {
        saving.value = false;
    }
}

async function reloadTest() {
    conflict.value = false;
    await loadTest();
}

function goProfile() {
    router.push({ name: 'profile' });
}

onMounted(initFromRoute);

// Переход /editor/A -> /editor/B в той же вкладке переиспользует компонент.
watch(
    () => route.params.id,
    () => initFromRoute(),
);
</script>

<style lang="css" src="./style.css" />

<template>
    <div class="constructor-page">
        <div v-if="isPublished" class="constructor-locked">
            Тест опубликован — редактирование недоступно.
            Чтобы внести изменения, снимите тест с публикации в профиле.
        </div>

        <fieldset class="constructor-fields" :disabled="isPublished">
            <div class="constructor-header">
                <input class="test-title" type="text" v-model="title" placeholder="Название теста" />
                <input class="test-desc" type="text" v-model="description" placeholder="Описание (необязательно)" />
            </div>

            <div class="questions-list" v-for="questionItem in questions" :key="questionItem.id">
                <div class="question-required-row">
                    <label class="required-toggle">
                        <input type="checkbox" v-model="questionItem.question.required" />
                        <span>Обязательный вопрос <span class="req-star">*</span></span>
                    </label>
                    <button class="remove-question" type="button" @click="removeQuestion(questionItem.id)">
                        Удалить вопрос
                    </button>
                </div>
                <div v-if="questionItem.question.type === QuestionType.One">
                    <OneCorrectComponent :question="questionItem.question" :answers="(questionItem.answers as OneCorrect[])" />
                </div>
                <div v-else-if="questionItem.question.type === QuestionType.Some">
                    <SomeCorrectComponent :question="questionItem.question" :answers="(questionItem.answers as SomeCorrect[])" />
                </div>
                <div v-else-if="questionItem.question.type === QuestionType.Match">
                    <MatchAnswersComponent :question="questionItem.question" :answers="(questionItem.answers as MatchAnswers[])" />
                </div>
                                <div v-else-if="questionItem.question.type === QuestionType.Text">
                    <TextAnswerComponent :question="questionItem.question" :answers="(questionItem.answers as TextAnswers[])" />
                </div>

                <ImageUploadComponent
                    v-if="questionItem.question.imageIds"
                    :image-ids="questionItem.question.imageIds"
                />
            </div>

            <div class="add-button-select">
                <label for="question">Форма ответа:</label>
                <select id="question-type" v-model="currentSelected">
                    <option :value="QuestionType.One">один правильный</option>
                    <option :value="QuestionType.Some">несколько правильных</option>
                    <option :value="QuestionType.Match">сопоставление</option>
                    <option :value="QuestionType.Text">текст</option>
                </select>
                <button id="add" @click="addQuestionItem()">Добавить</button>
            </div>
        </fieldset>

        <p v-if="error" class="constructor-error">{{ error }}</p>
        <div v-if="conflict" class="constructor-conflict">
            <span>Этот тест был изменён в другом окне. Ваши правки не сохранены, чтобы не затереть чужие.</span>
            <button type="button" @click="reloadTest">Загрузить актуальную версию</button>
        </div>
        <p v-if="message" class="constructor-message">{{ message }}</p>

        <div class="constructor-actions">
            <button
                :disabled="saving || !title || isPublished"
                :title="isPublished ? 'Тест опубликован — редактирование недоступно' : ''"
                @click="save(false)"
            >Сохранить</button>
            <button
                :disabled="saving || !title || isPublished"
                :title="isPublished ? 'Тест уже опубликован' : ''"
                @click="save(true)"
            >Опубликовать</button>
            <button class="secondary" @click="goProfile">К профилю</button>
        </div>
    </div>
</template>
