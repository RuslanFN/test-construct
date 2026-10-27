<script setup lang="ts">
import { ref } from 'vue';
import { Question, TextAnswers } from './schemas';
const props = defineProps<{
    question: Question;
    answers: TextAnswers[];
}>();
const answer = {id: 1, questionId: props.question.questionId, text: ""}
props.answers.push(answer);
/*
const answers = ref<answer[]>([])
function addanswer() {
      if (answers.value.length > 0) {
        const nextId = Math.max(...answers.value.map(a => a.id), 0) + 1;
        const ans = { id: nextId, text: "", text2: "" };
        answers.value.push(ans);
    } else {
        let ans = { id: 1, text: "", text2: "" };
        answers.value.push(ans);
    }
}*/
</script>
<template>
    <div class="question">
        <div class="question-text-container">
            <label for="quetion-text"> Введите текст вопроса:</label>
            <input type="text" id="question-text" name="question-text" />
        </div>
        <div class="text-ans-container" >
            <label for="answer"> Ответ</label>
            <input type="text" name="answer" v-model="answers[0].text" />

        </div>
    </div>
</template>  