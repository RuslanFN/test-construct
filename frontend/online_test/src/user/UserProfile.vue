<style lang="css" src="./profile.css" />
<template>
    <div class="profile-info">
        <div class="profile-item">
            <span class="profile-label">имя пользователя</span>
            <span class="profile-value">IVANOV</span>
        </div>
        <div class="profile-item">
            <span class="profile-label">Фамилия</span>
            <span class="profile-value">Иванов</span>
        </div>
        <div class="profile-item">
            <span class="profile-label">Имя</span>
            <span class="profile-value">Иван</span>
        </div>
        <div class="profile-item">
            <span class="profile-label">Отчество</span>
            <span class="profile-value">Иванович</span>
        </div>
        <div class="profile-item">
            <span class="profile-label">Почта</span>
            <span class="profile-value">ivanov.ivan@mail.ru</span>
        </div>
        <div class="profile-item">
            <span class="profile-label">Телефон</span>
            <span class="profile-value">+79012332121</span>
        </div>
    </div>
    <div class="tests-table">
        <table>
            <thead>
                <tr>
                    <th>Наименование теста</th>
                    <th>статус</th>
                    <th>Действия</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td>
                        test name
                    </td>
                    <td>
                        <span class="status status--published ">
                            опубликован
                        </span>
                    </td>
                    <td>
                        <button>
                            снять с публицации
                        </button>

                        <button>
                            редактировать
                        </button>
                        <button>
                            удалить
                        </button>
                    </td>
                </tr>
            </tbody>
        </table>
    </div>
</template>