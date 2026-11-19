<script setup>
import { computed } from 'vue';

const props = defineProps({
  total: { type: Number, required: true },
  page: { type: Number, required: true },
  pageSize: { type: Number, default: 10 },
});

const emit = defineEmits(['update:page']);

const pageCount = computed(() => Math.max(1, Math.ceil(props.total / props.pageSize)));

// Список номеров страниц с «окном» вокруг текущей (макс. 5 кнопок).
const pages = computed(() => {
  const count = pageCount.value;
  const cur = props.page;
  const span = 2;
  let start = Math.max(1, cur - span);
  let end = Math.min(count, cur + span);
  // добиваем окно до 5, если упёрлись в край
  if (end - start < 4) {
    if (start === 1) end = Math.min(count, start + 4);
    else start = Math.max(1, end - 4);
  }
  const out = [];
  for (let i = start; i <= end; i++) out.push(i);
  return out;
});

function go(p) {
  const count = pageCount.value;
  const next = Math.min(Math.max(1, p), count);
  if (next !== props.page) emit('update:page', next);
}
</script>

<template>
  <div v-if="total > 0" class="pagination">
    <button type="button" class="pagination-btn" :disabled="page <= 1" @click="go(page - 1)" title="Назад">‹</button>
    <button
      v-for="p in pages"
      :key="p"
      type="button"
      class="pagination-btn"
      :class="{ 'pagination-btn--active': p === page }"
      @click="go(p)"
    >{{ p }}</button>
    <button type="button" class="pagination-btn" :disabled="page >= pageCount" @click="go(page + 1)" title="Вперёд">›</button>
    <span class="pagination-info">Стр. {{ page }} из {{ pageCount }} · всего {{ total }}</span>
  </div>
</template>
