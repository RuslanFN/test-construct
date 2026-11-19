<script setup lang="ts">
import { ref, watch } from 'vue';
import { OneCorrect, Question } from './schemas';

const props = defineProps<{
    question: Question;
    answers: OneCorrect[]; 
}>();
// Инициализируем выбранный вариант из уже загруженных данных,
// иначе при открытии теста радио пустое, хотя правильный ответ есть.
const correctAnswer = ref<number | undefined>(
    props.answers.find(a => a.isCorrect)?.id
);

watch(correctAnswer, (newValue) => {
    if (newValue === undefined) return;
    props.answers.forEach(ans => {
        ans.isCorrect = (ans.id === newValue);
    });
})

function addanswer() {
    // uuid НЕ задаём: это новый вариант, сервер присвоит ему id при сохранении
    if (props.answers.length > 0) {
        const nextId = Math.max(...props.answers.map(a => a.id), 0) + 1;
        const ans = { id: nextId, text: "", isCorrect: false, questionId: props.question.questionId };
        props.answers.push(ans);
    } else {
        let ans = { id: 1, text: "", isCorrect: false, questionId: props.question.questionId };
        props.answers.push(ans);
    }
}

function removeAnswer(id: number) {
    const idx = props.answers.findIndex(a => a.id === id);
    if (idx >= 0) props.answers.splice(idx, 1);
    if (correctAnswer.value === id) correctAnswer.value = undefined;
}
</script>
<style lang="css" src="./style.css" />
<template>
    <div class="question">
        <div class="question-text-container">
                        <label for="question-text"> Введите текст вопроса:</label>
            <textarea id="question-text" name="question-text" rows="3" class="question-textarea" v-model="props.question.text"></textarea>
        </div>
        <div class="one-correct-ans-container" v-for="answer in props.answers" :key="answer.id">
            <label for="answer"> Ответ</label>
            <input type="text" name="answer" v-model="answer.text" />
            <input type="radio" :name="`answer-to-question-${answer.questionId}`" :value="answer.id"
                v-model="correctAnswer" />
            <button class="remove-ans" type="button" title="Удалить вариант" @click="removeAnswer(answer.id)">×</button>
        </div>
        <button id="add-ans" @click="addanswer()">добавить вариант ответа</button>
    </div>
</template>