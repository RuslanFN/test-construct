<style lang="css" src="./login.css" />
<template>
    <div class="login-form">
        <form>
            <h1>Войти</h1>
            <div class="login-field">
                <label for="username">имя пользовтеля</label>
                <input id="username" type="text" name="username" placeholder="Введите имя пользователя или email" />
            </div>
            <div class="password-field">
                <label for="password">пароль</label>
                <input type="password" id="password" name="password" placeholder="Введите пароль" />
            </div>
            <div class="button-submit">
                <button type="submit">Войти</button>
            </div>
        </form>
    </div>
</template>