<script setup lang="ts">
import { ref } from 'vue';
import {
    type QuestionItem,
    type OneCorrect,
    type SomeCorrect,
    type MatchAnswers,
    type TextAnswers,
    type AnyAnswer,
    QuestionType,

} from './schemas.ts'
import OneCorrectComponent from './OneCorrect.vue';
import SomeCorrectComponent from './SomeCorrect.vue';
import MatchAnswersComponent from './MatchAnswers.vue';
import TextAnswerComponent from './TextAnswer.vue';
const questions = ref<QuestionItem[]>([]);
const currentSelected = ref<QuestionType>(QuestionType.One)
function addQuestionItem() {
    console.log(questions.value)
    let newId = 1
    if (questions.value.length > 0) {
        newId = Math.max(...questions.value.map(q => q.id)) + 1;
    }
    let newQuestionItem: QuestionItem = {
        id: newId,
        question: {
            questionId: newId,
            type: currentSelected.value,
            text: ""
        },
        answers: []
    }
    questions.value.push(newQuestionItem)
}
</script>
<style lang="css" src="./style.css" />
<template>
    <div class="questions-list" v-for="questionItem in questions">
        <div v-if="questionItem.question.type === QuestionType.One">
            <OneCorrectComponent :question="questionItem.question" :answers="(questionItem.answers as OneCorrect[])" />
        </div>
        <div v-else-if="questionItem.question.type === QuestionType.Some">
            <SomeCorrectComponent :question="questionItem.question" :answers="(questionItem.answers as SomeCorrect[])" />
        </div>
        <div v-else-if="questionItem.question.type === QuestionType.Match">
            <MatchAnswersComponent :question="questionItem.question" :answers="(questionItem.answers as MatchAnswers[])"/>
        </div>
        <div v-else-if="questionItem.question.type === QuestionType.Text">
            <TextAnswerComponent :question="questionItem.question" :answers="(questionItem.answers as TextAnswers[])" />
        </div>
    </div>
    <div class="add-button-select">
        <label for="question">Форма ответа:</label>
        <select id="question-type" v-model="currentSelected">
            <option :value="QuestionType.One">один правильный</option>
            <option :value="QuestionType.Some">несколько правильных</option>
            <option :value="QuestionType.Match">сопоставление</option>
            <option :value="QuestionType.Text">текст</option>
        </select>
        <button id="add" v-on:click="addQuestionItem()">Добавить</button>
    </div>
</template>