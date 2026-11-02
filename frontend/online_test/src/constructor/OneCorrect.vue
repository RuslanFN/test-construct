<script setup lang="ts">
import { ref, watch } from 'vue';
import { OneCorrect, Question } from './schemas';

const props = defineProps<{
    question: Question;
    answers: OneCorrect[]; 
}>();
const correctAnswer = ref<number>();

watch(correctAnswer, (newValue, oldValue) => {
    if (newValue) {
        props.answers.forEach(ans => {
            ans.isCorrect = (ans.id === newValue);
        });
        console.log(props.answers);
    }
})

function addanswer() {
    if (props.answers.length > 0) {
        const nextId = Math.max(...props.answers.map(a => a.id), 0) + 1;
        const ans = { id: nextId, text: "", isCorrect: false, questionId: props.question.questionId };
        props.answers.push(ans);
    } else {
        let ans = { id: 1, text: "", isCorrect: false, questionId: props.question.questionId };
        props.answers.push(ans);
    }
}
</script>
<style lang="css" src="./style.css" />
<template>
    <div class="question">
        <div class="question-text-container">
            <label for="quetion-text"> Введите текст вопроса:</label>
            <input type="text" id="question-text" name="question-text" v-model="props.question.text"/>
        </div>
        <div class="one-correct-ans-container" v-for="answer in props.answers" :key="answer.id">
            <label for="answer"> Ответ</label>
            <input type="text" name="answer" v-model="answer.text" />
            <input type="radio" :name="`answer-to-question-${answer.questionId}`" :value="answer.id"
                v-model="correctAnswer" />
        </div>
        <button id="add-ans" @click="addanswer()">добавить вариант ответа</button>
    </div>
</template>