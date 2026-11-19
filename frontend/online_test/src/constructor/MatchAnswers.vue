<script setup lang="ts">
import { ref } from 'vue';
import { Question, MatchAnswers } from './schemas';
const props = defineProps<{
    question: Question;
    answers: MatchAnswers[];
}>();

function addanswer() {
    // новая пара — без uuid, сервер присвоит id при сохранении
    let nextId = 1; 
    if (props.answers.length > 0) {
        nextId = Math.max(...props.answers.map(a => a.id), 0) + 1;
    }
    const ans = { id: nextId, questionId: props.question.questionId, text1: "", text2: "" };
    props.answers.push(ans);
}

function removeAnswer(id: number) {
    const idx = props.answers.findIndex(a => a.id === id);
    if (idx >= 0) props.answers.splice(idx, 1);
}

// ---- drag-and-drop перестановка пар ----
// Индекс элемента, который сейчас перетаскивают (null — перетаскивания нет).
const dragIndex = ref<number | null>(null);
// Индекс элемента, над которым сейчас курсор (для подсветки места вставки).
const overIndex = ref<number | null>(null);

function onDragStart(event: DragEvent, index: number) {
    dragIndex.value = index;
    // В Firefox перетаскивание не начнётся без setData.
    event.dataTransfer?.setData('text/plain', String(index));
    if (event.dataTransfer) event.dataTransfer.effectAllowed = 'move';
}

function onDragOver(event: DragEvent, index: number) {
    // Разрешаем «бросать» в этот контейнер.
    event.preventDefault();
    if (event.dataTransfer) event.dataTransfer.dropEffect = 'move';
    if (dragIndex.value === null) return;
    if (index !== overIndex.value) overIndex.value = index;
}

function onDragLeave(index: number) {
    if (overIndex.value === index) overIndex.value = null;
}

function onDrop(event: DragEvent, index: number) {
    event.preventDefault();
    const from = dragIndex.value;
    resetDrag();
    if (from === null || from === index) return;

    // Перемещаем перетаскиваемый элемент на позицию index, остальные сдвигаются.
    const moved = props.answers.splice(from, 1)[0];
    props.answers.splice(index, 0, moved);
}

function onDragEnd() {
    resetDrag();
}

function resetDrag() {
    dragIndex.value = null;
    overIndex.value = null;
}
</script>
<style lang="css" src="./style.css" />
<template>
    <div class="question">
        <div class="question-text-container">
            <label for="question-text"> Введите текст вопроса:</label>
            <textarea id="question-text" name="question-text" rows="3" class="question-textarea" v-model="props.question.text"></textarea>
        </div>
        <p class="match-drag-hint">Перетащите пару за маркер <span class="match-drag-handle-hint">⠿</span>, чтобы изменить порядок.</p>
        <div
            class="match-ans-container"
            v-for="(answer, index) in props.answers"
            :key="answer.id"
            :class="{
                'match-dragging': dragIndex === index,
                'match-drop-target': overIndex === index && dragIndex !== index,
            }"
            @dragover="onDragOver($event, index)"
            @dragleave="onDragLeave(index)"
            @drop="onDrop($event, index)"
        >
            <span
                class="match-drag-handle"
                draggable="true"
                title="Перетащить"
                @dragstart="onDragStart($event, index)"
                @dragend="onDragEnd"
            >⠿</span>
            <label for="answer-1">определение 1</label>
            <input type="text" name="answer-1" v-model="answer.text1" />
            <label for="answer-2">определение 2</label>
            <input type="text" name="answer-2" v-model="answer.text2" />
            <button class="remove-ans" type="button" title="Удалить пару" @click="removeAnswer(answer.id)">×</button>
        </div>
        <button id="add-ans" @click="addanswer()">добавить вариант ответа</button>
    </div>
</template>