<script setup lang="ts">
import { ref } from 'vue';
import { api } from '../api';
import ImageCarousel from '../components/ImageCarousel.vue';
import '../components/carousel.css';

// Компонент загрузки изображений к вопросу.
// Работает с массивом id: родитель хранит image_ids, дети только добавляют/удаляют.
const props = defineProps<{
    imageIds: string[];
}>();

const uploading = ref(false);
const error = ref('');

// 5 МБ — жёсткий лимит (в проекте всего 5 ГБ хранилища)
const MAX_BYTES = 5 * 1024 * 1024;
const ALLOWED = ['image/png', 'image/jpeg', 'image/webp'];

function urlOf(id: string) {
    return api.mediaUrl(id);
}

const urls = () => props.imageIds.map(urlOf);

// Индекс текущего слайда — нужен, чтобы удалять именно то, что на экране.
// Карусель о своём индексе наружу не сообщает (у неё своё состояние),
// поэтому держим его здесь синхронно.
const currentIdx = ref(0);

function prevIdx() {
    const n = props.imageIds.length;
    currentIdx.value = (currentIdx.value - 1 + n) % Math.max(n, 1);
}

function nextIdx() {
    const n = props.imageIds.length;
    currentIdx.value = (currentIdx.value + 1) % Math.max(n, 1);
}

async function onPick(event: Event) {
    error.value = '';
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0];
    if (!file) return;

    // Предварительные проверки на клиенте — сервер проверит содержимое ещё раз.
    if (file.size > MAX_BYTES) {
        error.value = `Файл больше ${MAX_BYTES / (1024 * 1024)} МБ`;
        input.value = '';
        return;
    }
    if (!ALLOWED.includes(file.type)) {
        error.value = 'Разрешены только PNG, JPEG и WEBP';
        input.value = '';
        return;
    }

    uploading.value = true;
    try {
        const media = await api.uploadMedia(file);
        props.imageIds.push(media.id);
    } catch (e: any) {
        error.value = e.message;
    } finally {
        uploading.value = false;
        input.value = '';
    }
}

async function removeAt(idx: number) {
    const id = props.imageIds[idx];
    if (!id) return;
    // Убираем из вопроса; файл с сервера удалится при сохранении теста
    // (см. очистку «осиротевших» картинок на бэкенде).
    props.imageIds.splice(idx, 1);
    // Держим текущий слайд в границах оставшихся картинок.
    if (currentIdx.value >= props.imageIds.length) {
        currentIdx.value = Math.max(props.imageIds.length - 1, 0);
    }
}
</script>

<template>
    <div class="img-upload">
        <div v-if="imageIds.length" class="img-upload-preview">
            <ImageCarousel :urls="urls()" :framed="false" />
            <div class="img-upload-bar">
                <span class="img-upload-count">
                    Изображение {{ Math.min(currentIdx + 1, imageIds.length) }} из {{ imageIds.length }}
                </span>
                <button
                    type="button"
                    class="img-remove"
                    title="Удалить текущее изображение"
                    @click="removeAt(Math.min(currentIdx, imageIds.length - 1))"
                >Удалить текущее</button>
            </div>
        </div>
        <label class="img-add" :class="{ 'img-add--busy': uploading }">
            <input
                type="file"
                accept="image/png,image/jpeg,image/webp"
                :disabled="uploading"
                @change="onPick"
            />
            {{ uploading ? 'Загрузка…' : '+ Добавить изображение' }}
        </label>
        <p v-if="error" class="img-error">{{ error }}</p>
        <p class="img-hint">PNG, JPEG или WEBP, до 5 МБ. При нескольких изображениях показывается карусель.</p>
    </div>
</template>
