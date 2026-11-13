<script setup lang="ts">

import { Question, TextAnswers } from './schemas';
const props = defineProps<{
    question: Question;
    answers: TextAnswers[];
}>();

if (props.answers.length === 0) {
    props.answers.push({ id: 1, questionId: props.question.questionId, text: "" });
}
</script>
<style lang="css" src="./style.css" />
<template>
    <div class="question">
        <div class="question-text-container">
            <label for="quetion-text"> Введите текст вопроса:</label>
            <input type="text" id="question-text" name="question-text" v-model="props.question.text" />
        </div>
        <div class="text-ans-container">
            <label for="answer"> Правильный ответ</label>
            <input type="text" name="answer" v-model="props.answers[0].text" />
        </div>
    </div>
</template>
