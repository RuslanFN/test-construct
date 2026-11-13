<script setup lang="ts">
import { ref } from 'vue';
import { Question, MatchAnswers } from './schemas';
const props = defineProps<{
    question: Question;
    answers: MatchAnswers[];
}>();

function addanswer() {
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
</script>
<template>
    <div class="question">
        <div class="question-text-container">
            <label for="quetion-text"> Введите текст вопроса:</label>
            <input type="text" id="question-text" name="question-text" v-model="props.question.text" />
        </div>
        <div class="match-ans-container" v-for="answer in props.answers" :key="answer.id">
            <label for="answer-1">определение 1</label>
            <input type="text" name="answer-1" v-model="answer.text1" />
            <label for="answer-2">определение 2</label>
            <input type="text" name="answer-2" v-model="answer.text2" />
            <button class="remove-ans" type="button" title="Удалить пару" @click="removeAnswer(answer.id)">×</button>
        </div>
        <button id="add-ans" @click="addanswer()">добавить вариант ответа</button>
    </div>
</template>