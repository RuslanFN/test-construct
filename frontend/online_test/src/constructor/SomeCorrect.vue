<script setup lang="ts">
import { ref, watch } from 'vue';
import { Question, SomeCorrect } from './schemas';
const props = defineProps<{
    question: Question;
    answers: SomeCorrect[];
}>();


function addAnswer() {
    let nextId = 1;
    if (props.answers.length > 0) {
        nextId = Math.max(...props.answers.map(a => a.id), 0) + 1;
    }
    const ans = { id: nextId, text: "", isCorrect: false, questionId: props.question.questionId };
    props.answers.push(ans);
}
</script>
<template>
    <div class="question">
        <div class="question-text-container">
            <label for="quetion-text"> Введите текст вопроса:</label>
            <input type="text" id="question-text" name="question-text" />
        </div>
        <div class="one-correct-ans-container" v-for="answer in answers" :key="answer.id">
            <label for="answer"> Ответ</label>
            <input type="text" name="answer" v-model="answer.text" />
            <input type="checkbox" :name="`answer-to-question-${answer.questionId}`" v-model="answer.isCorrect" />
        </div>
        <button id="add-ans" @click="addAnswer()">добавить вариант ответа</button>
    </div>
</template>