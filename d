[1mdiff --git a/frontend/online_test/src/constructor/Constructor.vue b/frontend/online_test/src/constructor/Constructor.vue[m
[1mindex f371538..9fa1f37 100644[m
[1m--- a/frontend/online_test/src/constructor/Constructor.vue[m
[1m+++ b/frontend/online_test/src/constructor/Constructor.vue[m
[36m@@ -17,6 +17,7 @@[m [mimport TextAnswerComponent from './TextAnswer.vue';[m
 const questions = ref<QuestionItem[]>([]);[m
 const currentSelected = ref<QuestionType>(QuestionType.One)[m
 function addQuestionItem() {[m
[32m+[m[32m    console.log(questions.value)[m
     let newId = 1[m
     if (questions.value.length > 0) {[m
         newId = Math.max(...questions.value.map(q => q.id)) + 1;[m
[36m@@ -33,7 +34,7 @@[m [mfunction addQuestionItem() {[m
     questions.value.push(newQuestionItem)[m
 }[m
 </script>[m
[31m-[m
[32m+[m[32m<style lang="css" src="./style.css" />[m
 <template>[m
     <div class="questions-list" v-for="questionItem in questions">[m
         <div v-if="questionItem.question.type === QuestionType.One">[m
[1mdiff --git a/frontend/online_test/src/constructor/OneCorrect.vue b/frontend/online_test/src/constructor/OneCorrect.vue[m
[1mindex 712b417..2b436b0 100644[m
[1m--- a/frontend/online_test/src/constructor/OneCorrect.vue[m
[1m+++ b/frontend/online_test/src/constructor/OneCorrect.vue[m
[36m@@ -28,6 +28,7 @@[m [mfunction addanswer() {[m
     }[m
 }[m
 </script>[m
[32m+[m[32m<style lang="css" src="./style.css" />[m
 <template>[m
     <div class="question">[m
         <div class="question-text-container">[m
