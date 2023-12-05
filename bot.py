import telebot
from telebot import types
import sqlite3
from datetime import datetime
import threading

# Инициализация базы данных
db = sqlite3.connect("server.db", check_same_thread=False)
mysql = db.cursor()
lock = threading.Lock()

mysql.execute(
    "CREATE TABLE IF NOT EXISTS job_proposals (user_id INTEGER, username TEXT, proposal_text TEXT, timestamp TEXT)")
mysql.execute("CREATE TABLE IF NOT EXISTS admins (password TEXT)")

# создание токена
botTimeWeb = telebot.TeleBot('6612819709:AAFR2YvqPU7oVblZ4DWHlD9Yvyu0wb6Ms2w')

# Словарь для отслеживания состояний пользователей (в меню, оставление предложения или нет)
user_states = {}

# Словарь для хранения времени оставления предложения
proposal_timestamps = {}

@botTimeWeb.message_handler(commands=['start'])
def startBot(message):
    with lock:
        first_mess = (
            f"<b>{message.from_user.first_name} {message.from_user.last_name}</b>, привет!\nХочешь расскажу "
            f"немного о нашей компании:")

        # Создание кастомной клавиатуры
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        item_reports = types.KeyboardButton("Работа с данными")
        item_website = types.KeyboardButton("Перейти на сайт")
        item_propose = types.KeyboardButton("Оставить предложение о работе")
        item_exit = types.KeyboardButton("Выход")

        markup.add(item_reports, item_website, item_propose, item_exit)

        botTimeWeb.send_message(message.chat.id, first_mess, parse_mode='html', reply_markup=markup)
        user_states[message.chat.id] = "in_menu"


@botTimeWeb.message_handler(func=lambda message: True)
def handle_messages(message):
    with lock:
        user_state = user_states.get(message.chat.id)

        if user_state == "in_menu":
            if message.text == 'Работа с данными':
                # Запрашиваем пароль у пользователя
                botTimeWeb.send_message(message.chat.id, "Введите пароль для просмотра отчетов:")

                user_states[message.chat.id] = "enter_password_reports"

            elif message.text == 'Перейти на сайт':
                second_mess = "Более детально со мной ты можешь ознакомиться на сайте!"
                markup = types.InlineKeyboardMarkup()
                markup.add(types.InlineKeyboardButton("Перейти на сайт", url="https://www.bsuir.by"))
                botTimeWeb.send_message(message.chat.id, second_mess, reply_markup=markup)
                botTimeWeb.answer_callback_query(callback_query_id=message.id)

            elif message.text == 'Оставить предложение о работе':
                botTimeWeb.send_message(message.chat.id, "Оставьте ваше предложение о работе:")
                user_states[message.chat.id] = "propose_job"

            elif message.text == 'Выход':
                # Логика выхода из меню
                markup = types.ReplyKeyboardRemove()
                botTimeWeb.send_message(message.chat.id, "Вы вышли из меню.", reply_markup=markup)
                user_states[message.chat.id] = "out_of_menu"
            elif message.text == '/exit':
                # Логика выхода из бота
                botTimeWeb.send_message(message.chat.id, "До свидания! Если захотите вернуться, просто напишите /start.")
                user_states.pop(message.chat.id, None)
        elif user_state == "enter_password_reports":
            # Проверяем введенный пароль

            # Словарь для хранения паролей админов
            admin_passwords = set(mysql.execute("SELECT password FROM admins").fetchall())

            entered_password = message.text
            if entered_password in admin_passwords:
                # Пользователь ввел правильный пароль, отображаем отчеты
                reports = mysql.execute("SELECT * FROM job_proposals").fetchall()
                reports_text = '\n'.join(
                    [f'User ID: {report[0]}, Текст: {report[2]}, Временная метка: {report[3]}' for report in reports])

                # Добавляем клавиатуру для предложения удалить данные
                markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
                item_delete = types.KeyboardButton("Удалить данные")
                markup.add(item_delete)

                botTimeWeb.send_message(message.chat.id, f"Отчеты:\n{reports_text}", reply_markup=markup)
                user_states[message.chat.id] = "reports_menu"
            else:
                botTimeWeb.send_message(message.chat.id, "Неверный пароль. Попробуйте еще раз:")
                user_states[message.chat.id] = "enter_password_reports"

        elif user_state == "reports_menu":
            if message.text == "Удалить данные":
                # Пользователь хочет удалить данные, предложим подтверждение
                confirm_markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
                item_confirm = types.KeyboardButton("Подтвердить удаление")
                item_cancel = types.KeyboardButton("Отмена")
                confirm_markup.row(item_confirm, item_cancel)
                botTimeWeb.send_message(message.chat.id, "Вы уверены, что хотите удалить данные?", reply_markup=confirm_markup)
                user_states[message.chat.id] = "confirm_delete"

        elif user_state == "confirm_delete":
            if message.text == "Подтвердить удаление":
                # Логика удаления данных (замените на свою)
                # Например, можно использовать SQL-запрос для удаления данных из базы данных
                mysql.execute("DELETE FROM job_proposals WHERE user_id=?", (message.chat.id,))
                db.commit()

                botTimeWeb.send_message(message.chat.id, "Данные успешно удалены.")
            elif message.text == "Отмена":
                botTimeWeb.send_message(message.chat.id, "Удаление данных отменено.")

                # Возвращаем пользователя в основное меню
                user_states[message.chat.id] = "in_menu"

        elif user_state == "propose_job":
            # Пользователь оставляет предложение о работе
            proposal_text = message.text
            proposal_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            proposal_timestamps[message.chat.id] = proposal_timestamp

            # Отправляем уведомление администратору
            admin_chat_id = 1061011426  # Замените на ID вашего аккаунта в Telegram
            admin_notification = f"Новое предложение о работе:\n\nОт пользователя {message.from_user.username}:\n{proposal_text}"
            botTimeWeb.send_message(admin_chat_id, admin_notification)
            admin_markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
            admin_markup.add(types.KeyboardButton("Игнорировать"))
            botTimeWeb.send_message(message.chat.id, f"Спасибо за предложение! Ожидайте рассмотрения.")

            # Сохраняем предложение в базе данных
            mysql.execute("INSERT INTO job_proposals (user_id, username, proposal_text, timestamp) VALUES (?, ?, ?, ?)",
                          (message.chat.id, message.from_user.username, proposal_text, proposal_timestamp))
            db.commit()

            # Возвращаем пользователя в основное меню
            user_states[message.chat.id] = "in_menu"


botTimeWeb.infinity_polling()
