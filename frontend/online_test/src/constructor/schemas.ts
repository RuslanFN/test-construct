export enum QuestionType{
    One = 'one',
    Some = 'some',
    Match = 'match',
    Text = 'text'
}
export interface Answer {
    id: number;
    questionId: number; 
}
export interface Question {
    questionId: number;
    text: string;
    type: QuestionType;
    required?: boolean;
}
export interface OneCorrect extends Answer {
    text: string;
    isCorrect: boolean;
}
export interface SomeCorrect extends Answer {
    text: string;
    isCorrect: boolean;
}
export interface MatchAnswers extends Answer {
    text1: string;
    text2: string;
}
export interface TextAnswers extends Answer {
    text: string;
}

export type AnyAnswer = OneCorrect | SomeCorrect | MatchAnswers | TextAnswers;
export interface QuestionItem{
    id: number;
    question: Question;
    answers: AnyAnswer[];
}