<script setup lang="ts">
import { ref, watch } from 'vue';
import { Question, SomeCorrect } from './schemas';
const props = defineProps<{
    question: Question;
    answers: SomeCorrect[];
}>();


function addAnswer() {
    // новый вариант — без uuid, сервер присвоит id при сохранении
    let nextId = 1;
    if (props.answers.length > 0) {
        nextId = Math.max(...props.answers.map(a => a.id), 0) + 1;
    }
    const ans = { id: nextId, text: "", isCorrect: false, questionId: props.question.questionId };
    props.answers.push(ans);
}

function removeAnswer(id: number) {
    const idx = props.answers.findIndex(a => a.id === id);
    if (idx >= 0) props.answers.splice(idx, 1);
}
</script>
<template>
    <div class="question">
        <div class="question-text-container">
                        <label for="question-text"> Введите текст вопроса:</label>
            <textarea id="question-text" name="question-text" rows="3" class="question-textarea" v-model="props.question.text"></textarea>
        </div>
        <div class="one-correct-ans-container" v-for="answer in answers" :key="answer.id">
            <label for="answer"> Ответ</label>
            <input type="text" name="answer" v-model="answer.text" />
            <input type="checkbox" :name="`answer-to-question-${answer.questionId}`" v-model="answer.isCorrect" />
            <button class="remove-ans" type="button" title="Удалить вариант" @click="removeAnswer(answer.id)">×</button>
        </div>
        <button id="add-ans" @click="addAnswer()">добавить вариант ответа</button>
    </div>
</template>