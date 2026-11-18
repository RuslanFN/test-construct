<script setup lang="ts">
import { computed, ref } from 'vue';

// Карусель изображений: показывает одно фото за раз, листается стрелками,
// точками и клавишами ← →. Используется и в конструкторе, и при прохождении.
const props = withDefaults(defineProps<{
    urls: string[];
    alt?: string;
    // рамка/фон удобно отключать в конструкторе, где свои стили карточки
    framed?: boolean;
}>(), {
    alt: 'Изображение к вопросу',
    framed: true,
});

const current = ref(0);

const total = computed(() => props.urls.length);
const hasMany = computed(() => total.value > 1);

// При удалении картинок индекс может выйти за границы — подстраховываемся.
const safeIndex = computed(() => Math.min(current.value, Math.max(total.value - 1, 0)));

function go(delta: number) {
    if (!hasMany.value) return;
    const next = safeIndex.value + delta;
    // листаем по кругу
    current.value = (next + total.value) % total.value;
}

function goTo(i: number) {
    current.value = i;
}

function onKey(event: KeyboardEvent) {
    if (event.key === 'ArrowLeft') {
        event.preventDefault();
        go(-1);
    } else if (event.key === 'ArrowRight') {
        event.preventDefault();
        go(1);
    }
}
</script>

<template>
    <div
        v-if="total > 0"
        class="img-carousel"
        :class="{ 'img-carousel--framed': framed }"
        tabindex="0"
        @keydown="onKey"
    >
        <div class="img-carousel-stage">
            <button
                v-if="hasMany"
                type="button"
                class="img-carousel-arrow img-carousel-arrow--prev"
                title="Предыдущее изображение"
                @click="go(-1)"
            >‹</button>

            <img
                :src="urls[safeIndex]"
                :alt="alt"
                loading="lazy"
                draggable="false"
            />

            <button
                v-if="hasMany"
                type="button"
                class="img-carousel-arrow img-carousel-arrow--next"
                title="Следующее изображение"
                @click="go(1)"
            >›</button>

            <span v-if="hasMany" class="img-carousel-counter">
                {{ safeIndex + 1 }} / {{ total }}
            </span>
        </div>

        <div v-if="hasMany" class="img-carousel-dots">
            <button
                v-for="(url, i) in urls"
                :key="url"
                type="button"
                class="img-carousel-dot"
                :class="{ 'img-carousel-dot--active': i === safeIndex }"
                :title="`Изображение ${i + 1}`"
                @click="goTo(i)"
            />
        </div>
    </div>
</template>
