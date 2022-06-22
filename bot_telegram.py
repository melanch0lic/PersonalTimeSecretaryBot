import asyncio
from msilib.schema import Error

import sqlite3
import time
from aiogram import Bot, types
from aiogram.dispatcher import Dispatcher
from aiogram.utils import executor
from aiogram.dispatcher.filters import Text

import requests
import speech_recognition as sr
import subprocess
from datetime import datetime
import os
import config
import sqlite3
import re

from aiogram.utils.exceptions import (
    MessageCantBeDeleted, MessageToDeleteNotFound)


my_token = config.API_TOKEN

bot = Bot(token=my_token)
dp = Dispatcher(bot)
logfile = str(datetime.today()) + '.log'


def audio_to_text(dest_name: str):
    # Функция для перевода аудио, в формате ".wav" в текст
    r = sr.Recognizer()  # такое вообще надо комментить?
    # тут мы читаем наш .wav файл
    message = sr.AudioFile(dest_name)
    with message as source:
        audio = r.record(source)
    # используя возможности библиотеки распознаем текст, так же тут можно изменять язык распознавания
    result = r.recognize_google(audio, language="ru_RU")
    return result


def insertEventToSql(event_name, event_datetime, user_id):
    try:
        conn = sqlite3.connect("data.db")
        cursor = conn.cursor()
        check_event = f"SELECT event_name FROM EVENTS WHERE EXISTS(SELECT event_id FROM EVENTS WHERE event_name='{event_name}') AND event_name='{event_name}'"
        resp = cursor.execute(check_event).fetchall()
        if not resp:
            sqlite_insert_query = f"INSERT INTO EVENTS (event_id, event_name, event_datetime, user_id) VALUES (null, '{event_name}', '{event_datetime}', '{user_id}')"
            cursor.execute(sqlite_insert_query)
            conn.commit()
            print('Запись успешно вставлена ​​в таблицу EVENTS', cursor.rowcount)
        else:
            print('Запись с таким событием уже существует')
        cursor.close()
    except sqlite3.Error as error:
        print('Ошибка при добавлении события в базу', error)
    finally:
        if conn:
            conn.close()
            print("Соединение с SQLite закрыто")


def getAllEvents(user_id):
    try:
        conn = sqlite3.connect("data.db")
        cursor = conn.cursor()

        sqlite_insert_query = f"SELECT * from EVENTS WHERE user_id='{user_id}'"
        resp = cursor.execute(sqlite_insert_query).fetchall()
        conn.commit()
        print("Все данные из таблицы EVENTS получены")
        cursor.close()
        return resp
    except sqlite3.Error as error:
        print('Ошибка при взятии событий из базы', error)
    finally:
        if conn:
            conn.close()
            print("Соединение с SQLite закрыто")


def deleteEvent(event_id):
    try:
        conn = sqlite3.connect("data.db")
        cursor = conn.cursor()

        sqlite_insert_query = f"DELETE from EVENTS WHERE event_id={event_id}"
        cursor.execute(sqlite_insert_query)
        conn.commit()
        print("Все данные из таблицы EVENTS получены")
        cursor.close()
    except sqlite3.Error as error:
        print('Ошибка при взятии событий из базы', error)
    finally:
        if conn:
            conn.close()
            print("Соединение с SQLite закрыто")


async def on_startup(_):
    print('Бот вышел в онлайн')
    try:
        conn = sqlite3.connect("data.db")
        cursor = conn.cursor()

        print(datetime.now())
        cursor.execute(
            ''' SELECT count(name) FROM sqlite_master WHERE type='table' AND name='EVENTS' ''')
        if cursor.fetchone()[0] == 1:
            print('Table exists!')
        else:
            cursor.execute(
                "CREATE TABLE EVENTS(event_id INTEGER PRIMARY KEY, event_name TEXT, event_datetime TEXT, user_id TEXT)")

        print("Подключен к SQLite")

    except sqlite3.Error as error:
        print("Ошибка при работе с SQLite", error)
    finally:
        if conn:
            conn.close()
            print("Соединение с SQLite закрыто")


@dp.message_handler(commands=['start', 'help'])
async def command_start(message: types.Message):
    try:
        start_buttons = ['✍Показать список', '👀О боте', ]
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
        keyboard.add(*start_buttons)
        await bot.send_message(message.from_user.id, 'Привет, для добавления задачи отправьте голосовое, содержащее дату, время, место события(если оно есть) или же текстовое сообщение такого же характера.', reply_markup=keyboard)
        await message.delete()

    except:
        await message.reply('Общение с ботом через ЛС, напишите ему: \nhttps://t.me/personal_secretarybot ')


@dp.message_handler(Text(equals='✍Показать список'))
async def get_list(message: types.Message):
    event_list = getAllEvents(message.from_user.id)
    if event_list:
        for i, value in enumerate(event_list):
            buttons = [types.InlineKeyboardButton(
                text='✅', callback_data=f'accept|{value[0]}|{value[1]}')]
            inline = types.InlineKeyboardMarkup(row_width=1)
            inline.add(*buttons)
            msg = await bot.send_message(message.from_user.id, f'{i+1}# {value[1]} {value[2]}', reply_markup=inline)
    else:
        await bot.send_message(message.from_user.id, 'Список напоминаний пуст.')
    print(event_list)


@dp.callback_query_handler(Text(startswith='accept'))
async def delete_event(query: types.CallbackQuery):
    await bot.delete_message(chat_id=query.from_user.id, message_id=query.message.message_id)
    info = query.data.split('|')
    await bot.send_message(query.from_user.id, f'Задача завершена - "{info[2]}"')
    deleteEvent(info[1])


@dp.message_handler(Text(equals='👀О боте'))
async def about_bot(message: types.Message):
    await bot.send_message(message.from_user.id, 'Этот бот написан в качестве курсовой работы \nСтарайтесь не судить строго ленивого студента 🥺')


@dp.message_handler(content_types=['voice'])
async def get_audio_messages(message):
    # Основная функция, принимает голосовуху от пользователя
    try:
        print("Started recognition...")
        # Ниже пытаемся вычленить имя файла, да и вообще берем данные с мессаги
        file_info = await bot.get_file(message.voice.file_id)
        path = file_info.file_path
        print(path)  # Вот тут-то и полный путь до файла (например: voice/file_2.oga)
        # Преобразуем путь в имя файла (например: file_2.oga)
        fname = os.path.basename(path)
        # Получаем и сохраняем присланную голосвуху (Ага, админ может в любой момент отключить удаление айдио файлов и слушать все, что ты там говоришь. А представь, что такую бяку подселят в огромный чат и она будет просто логировать все сообщения [анонимность в телеграмме, ахахаха])
        doc = requests.get(
            'https://api.telegram.org/file/bot{0}/{1}'.format(my_token, path))
        with open(fname, 'wb') as f:
            # вот именно тут и сохраняется сама аудио-мессага
            f.write(doc.content)
        # здесь используется страшное ПО ffmpeg, для конвертации .oga в .wav
        output = subprocess.call(['ffmpeg', '-i', fname,
                                  'output.wav'])
        # Вызов функции для перевода аудио в текст
        result = audio_to_text('output.wav')

        try:
            message_text = result.lower()

            for i in date_combinations.keys():
                if message_text.find(i) != -1:
                    print(i)
                    message_text = message_text.replace(
                        i, date_combinations[i])
                    break

            day_number = datetime.now().strftime('%d')
            month_number = datetime.now().strftime('%m')
            hour_number = datetime.now().strftime('%H')
            minute_number = datetime.now().strftime('%M')
            year_number = datetime.now().strftime('%Y')

            user_id = message.from_user.id
            event_id = 0
            event_name = ''
            event_datetime = ''

            is_month_exist = False

            for month in MONTHS.keys():
                if re.findall(r'\d+'+f' {month}', message_text):
                    temp_daymonth = re.findall(
                        r'\d+'+f' {month}', message_text)[0].split(' ')
                    day_number = temp_daymonth[0]
                    event_name = message_text.replace(re.findall(
                        r'\d+'+f' {month}', message_text)[0], '').strip()
                    month_number = MONTHS[month]
                    try:
                        valid_date = time.strptime(
                            f'{month_number}/{day_number}', '%m/%d')
                        is_month_exist = True
                    except ValueError:
                        print('Invalid date!')
                        await bot.send_message(message.from_user.id, 'Неправильный формат даты')
                        return Error
                    break

            first_date_time = re.findall(r'\d\d\:\d\d', message_text)
            second_date_time = re.findall(r'\d\:\d\d', message_text)
            third_date_time = re.findall(r'через \d+ ча\w+', message_text)
            fourth_date_time = re.findall(r'через \d+ мину\w+', message_text)
            fifth_date_time = re.findall(
                r'через \d+ ча\w+ и \d+ мину\w+', message_text)
            six_date_time = re.findall(
                r'через \d+ ча\w+ \d+ мину\w+', message_text)
            if first_date_time or second_date_time or third_date_time or fourth_date_time or fifth_date_time or six_date_time or is_month_exist:
                await message.reply('Есть время')
                if first_date_time:
                    temp_time = first_date_time[0].split(':')
                    hour_number = temp_time[0]
                    minute_number = temp_time[1]
                    event_name = message_text.replace(first_date_time[0], '').strip().strip(
                        'в').strip('к').strip('с').strip()
                    print(message_text)

                if second_date_time and not first_date_time:
                    temp_time = second_date_time[0].split(':')
                    hour_number = temp_time[0]
                    minute_number = temp_time[1]
                    event_name = message_text.replace(second_date_time[0], '').strip().strip(
                        'в').strip('к').strip('с').strip()

                if third_date_time and not (fifth_date_time or six_date_time):
                    temp_time = third_date_time[0].split(' ')
                    day_number = str(int(day_number) +
                                     (int(hour_number) + int(temp_time[1]))//24)
                    hour_number = str(int(hour_number) +
                                      int(temp_time[1]) % 24)
                    event_name = message_text.replace(third_date_time[0], '').strip().strip(
                        'в').strip('к').strip('с').strip()

                if fourth_date_time:
                    temp_time = fourth_date_time[0].split(' ')
                    hour_number = str(int(hour_number) + int(temp_time[1])//60)
                    minute_number = str(
                        int(minute_number) + int(temp_time[1]) % 60)
                    day_number = str(int(day_number) + int(hour_number)//24)
                    hour_number = str(int(hour_number) % 24)
                    event_name = message_text.replace(fourth_date_time[0], '').strip().strip(
                        'в').strip('к').strip('с').strip()

                if fifth_date_time or six_date_time:
                    if fifth_date_time:
                        temp_time = fifth_date_time[0].split(' ')
                        total_minutes = int(
                            temp_time[4]) + int(temp_time[1])*60
                        hour_number = str(
                            int(hour_number) + int(total_minutes)//60)
                        minute_number = str(int(minute_number) +
                                            int(total_minutes) % 60)
                        day_number = str(int(day_number) +
                                         int(hour_number)//24)
                        hour_number = str(int(hour_number) % 24)
                    else:
                        temp_time = six_date_time[0].split(' ')
                        total_minutes = int(
                            temp_time[3]) + int(temp_time[1])*60
                        hour_number = str(
                            int(hour_number) + int(total_minutes)//60)
                        minute_number = str(int(minute_number) +
                                            int(total_minutes) % 60)
                        day_number = str(int(day_number) +
                                         int(hour_number)//24)
                        hour_number = str(int(hour_number) % 24)

                if message_text.find('через час') != -1:
                    day_number = str(int(day_number) +
                                     (int(hour_number) + 1)//24)
                    hour_number = str(int(hour_number) + 1 % 24)
                event_datetime = f'{day_number}/{month_number}/{year_number} {hour_number}:{minute_number}'
                print(day_number, month_number,
                      hour_number, ':', minute_number)
                insertEventToSql(event_name, event_datetime, user_id)
                await task_notifications(event_name, message.from_user.id, (datetime.strptime(event_datetime, '%d/%m/%Y %H:%M') - datetime.strptime(datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "%Y-%m-%d %H:%M:%S")).seconds)
            else:
                await bot.send_message(message.from_user.id, 'Неккоректный ввод, попробуйте еще раз')
        except Exception as e:
            print(f'Ошибка {str(e)}')
            os.remove('output.wav')
            os.remove(fname)
    except sr.UnknownValueError as e:
        # Ошибка возникает, если сообщение не удалось разобрать. В таком случае отсылается ответ пользователю и заносим запись в лог ошибок
        await bot.send_message(message.from_user.id,  "Прошу прощения, но я не разобрал сообщение, или оно пустое...")
        with open(logfile, 'a', encoding='utf-8') as f:
            f.write(str(datetime.today().strftime("%H:%M:%S")) + ':' + str(message.from_user.id) + ':' + str(message.from_user.first_name) + '_' +
                    str(message.from_user.last_name) + ':' + str(message.from_user.username) + ':' + str(message.from_user.language_code) + ':Message is empty.\n')
    except Exception as e:
        # В случае возникновения любой другой ошибки, отправляется соответствующее сообщение пользователю и заносится запись в лог ошибок
        await bot.send_message(message.from_user.id,  "Что-то пошло плохо, но наши смелые инженеры уже трудятся над решением... \nДа ладно, никто эту ошибку исправлять не будет, она просто потеряется в логах.")
        with open(logfile, 'a', encoding='utf-8') as f:
            f.write(str(datetime.today().strftime("%H:%M:%S")) + ':' + str(message.from_user.id) + ':' + str(message.from_user.first_name) + '_' +
                    str(message.from_user.last_name) + ':' + str(message.from_user.username) + ':' + str(message.from_user.language_code) + ':' + str(e) + '\n')
    finally:
        os.remove('output.wav')
        os.remove(fname)

date_combinations = {
    'в 1:00 ночи': '1:00',
    'в 2:00 ночи': '2:00',
    'в 3:00 ночи': '3:00',
    'в 4:00 утра': '4:00',
    'в 4:00 ночи': '4:00',
    'в 5:00 утра': '5:00',
    'в 5:00 ночи': '5:00',
    'в 6:00 утра': '6:00',
    'в 7:00 утра': '7:00',
    'в 8:00 утра': '8:00',
    'в 9:00 утра': '9:00',
    'в 10:00 утра': '10:00',
    'в 11:00 утра': '11:00',
    'в 12:00 утра': '12:00',
    'в 1:00 дня': '13:00',
    'в 2:00 дня': '14:00',
    'в 3:00 дня': '15:00',
    'в 5:00 вечера': '17:00',
    'в 6:00 вечера': '18:00',
    'в 7:00 вечера': '19:00',
    'в 8:00 вечера': '20:00',
    'в 9:00 вечера': '21:00',
    'в 10:00 вечера': '22:00',
    'в 11:00 вечера': '23:00',
    'в 12:00 ночи': '0:00'
}

MONTHS = {
    'января': '01',
    'февраля': '02',
    'марта': '03',
    'апреля': '04',
    'мая': '05',
    'июня': '06',
    'июля': '07',
    'августа': '08',
    'сентября': '09',
    'октябра': '10',
    'ноября': '11',
    'декабря': '12'}


@dp.message_handler()
async def echo_send(message: types.Message):
    try:
        message_text = message.text.lower()

        for i in date_combinations.keys():
            if message_text.find(i) != -1:
                print(i)
                message_text = message_text.replace(i, date_combinations[i])
                break

        day_number = datetime.now().strftime('%d')
        month_number = datetime.now().strftime('%m')
        hour_number = datetime.now().strftime('%H')
        minute_number = datetime.now().strftime('%M')
        year_number = datetime.now().strftime('%Y')

        user_id = message.from_user.id
        event_id = 0
        event_name = ''
        event_datetime = ''

        is_month_exist = False

        for month in MONTHS.keys():
            if re.findall(r'\d+'+f' {month}', message_text):
                temp_daymonth = re.findall(
                    r'\d+'+f' {month}', message_text)[0].split(' ')
                day_number = temp_daymonth[0]
                event_name = message_text.replace(re.findall(
                    r'\d+'+f' {month}', message_text)[0], '').strip()
                month_number = MONTHS[month]
                try:
                    valid_date = time.strptime(
                        f'{month_number}/{day_number}', '%m/%d')
                    is_month_exist = True
                except ValueError:
                    print('Invalid date!')
                    await bot.send_message(message.from_user.id, 'Неправильный формат даты')
                    return Error
                break

        first_date_time = re.findall(r'\d\d\:\d\d', message_text)
        second_date_time = re.findall(r'\d\:\d\d', message_text)
        third_date_time = re.findall(r'через \d+ ча\w+', message_text)
        fourth_date_time = re.findall(r'через \d+ мину\w+', message_text)
        fifth_date_time = re.findall(
            r'через \d+ ча\w+ и \d+ мину\w+', message_text)
        six_date_time = re.findall(
            r'через \d+ ча\w+ \d+ мину\w+', message_text)
        if first_date_time or second_date_time or third_date_time or fourth_date_time or fifth_date_time or six_date_time or is_month_exist:
            await message.reply('Есть время')
            if first_date_time:
                temp_time = first_date_time[0].split(':')
                hour_number = temp_time[0]
                minute_number = temp_time[1]
                event_name = message_text.replace(first_date_time[0], '').strip().strip(
                    'в').strip('к').strip('с').strip()
                print(message_text)

            if second_date_time and not first_date_time:
                temp_time = second_date_time[0].split(':')
                hour_number = temp_time[0]
                minute_number = temp_time[1]
                event_name = message_text.replace(second_date_time[0], '').strip().strip(
                    'в').strip('к').strip('с').strip()

            if third_date_time and not (fifth_date_time or six_date_time):
                temp_time = third_date_time[0].split(' ')
                day_number = str(int(day_number) +
                                 (int(hour_number) + int(temp_time[1]))//24)
                hour_number = str(int(hour_number) + int(temp_time[1]) % 24)
                event_name = message_text.replace(third_date_time[0], '').strip().strip(
                    'в').strip('к').strip('с').strip()

            if fourth_date_time:
                temp_time = fourth_date_time[0].split(' ')
                hour_number = str(int(hour_number) + int(temp_time[1])//60)
                minute_number = str(int(minute_number) +
                                    int(temp_time[1]) % 60)
                day_number = str(int(day_number) + int(hour_number)//24)
                hour_number = str(int(hour_number) % 24)
                event_name = message_text.replace(fourth_date_time[0], '').strip().strip(
                    'в').strip('к').strip('с').strip()

            if fifth_date_time or six_date_time:
                if fifth_date_time:
                    temp_time = fifth_date_time[0].split(' ')
                    total_minutes = int(temp_time[4]) + int(temp_time[1])*60
                    hour_number = str(int(hour_number) +
                                      int(total_minutes)//60)
                    minute_number = str(int(minute_number) +
                                        int(total_minutes) % 60)
                    day_number = str(int(day_number) + int(hour_number)//24)
                    hour_number = str(int(hour_number) % 24)
                else:
                    temp_time = six_date_time[0].split(' ')
                    total_minutes = int(temp_time[3]) + int(temp_time[1])*60
                    hour_number = str(int(hour_number) +
                                      int(total_minutes)//60)
                    minute_number = str(int(minute_number) +
                                        int(total_minutes) % 60)
                    day_number = str(int(day_number) + int(hour_number)//24)
                    hour_number = str(int(hour_number) % 24)

            if message_text.find('через час') != -1:
                day_number = str(int(day_number) + (int(hour_number) + 1)//24)
                hour_number = str(int(hour_number) + 1 % 24)
            event_datetime = f'{day_number}/{month_number}/{year_number} {hour_number}:{minute_number}'
            print(day_number, month_number, hour_number, ':', minute_number)
            insertEventToSql(event_name, event_datetime, user_id)
            await task_notifications(event_name, message.from_user.id, (datetime.strptime(event_datetime, '%d/%m/%Y %H:%M') - datetime.strptime(datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "%Y-%m-%d %H:%M:%S")).seconds)
        else:
            await bot.send_message(message.from_user.id, 'Неккоректный ввод, попробуйте еще раз')
    except Exception as e:
        print(f'Ошибка {str(e)}')


async def task_notifications(message: str = '', user_id: int = 0, sleep_time: int = 0):
    if sleep_time - 3600 >= 0:
        sl = sleep_time - 3600
        await asyncio.sleep(sl)
        await bot.send_message(user_id, f'Через час у вас задача - "{message}"')
    await asyncio.sleep(sleep_time)
    await bot.send_message(user_id, f'Задача завершена - "{message}"')
    await bot.send_message(user_id, f'Удалите задачу из списка - "{message}"')

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True, on_startup=on_startup)
