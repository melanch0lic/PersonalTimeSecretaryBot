import sqlite3
from aiogram import Bot, types
from aiogram.dispatcher import Dispatcher
from aiogram.utils import executor
import requests
import speech_recognition as sr
import subprocess
import datetime
import os
import config
import sqlite3

my_token = config.API_TOKEN

bot = Bot(token=my_token)
dp = Dispatcher(bot)
logfile = str(datetime.date.today()) + '.log'
conn = sqlite3.connect("data.db")
cur = conn.cursor()


def audio_to_text(dest_name: str):
    # Функция для перевода аудио, в формате ".vaw" в текст
    r = sr.Recognizer()  # такое вообще надо комментить?
    # тут мы читаем наш .vaw файл
    message = sr.AudioFile(dest_name)
    with message as source:
        audio = r.record(source)
    # используя возможности библиотеки распознаем текст, так же тут можно изменять язык распознавания
    result = r.recognize_google(audio, language="ru_RU")
    return result

async def on_startup(_):
    print('Бот вышел в онлайн')


@dp.message_handler(commands=['start', 'help'])
async def command_start(message: types.Message):
    try:
        await bot.send_message(message.from_user.id, 'Привет, для добавления задачи отправьте голосовое, содержащее дату, время, место события(если оно есть)')
        await message.delete()
    except:
        await message.reply('Общение с ботом через ЛС, напишите ему: \nhttps://t.me/personal_secretarybot ')


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
            'https://api.telegram.org/file/bot{0}/{1}'.format('5595891998:AAEimVr-7ybYEteTRFskQuiS6s_Dh1L_s14', path))
        with open(fname, 'wb') as f:
            # вот именно тут и сохраняется сама аудио-мессага
            f.write(doc.content)
        # здесь используется страшное ПО ffmpeg, для конвертации .oga в .vaw
        output = subprocess.call(['ffmpeg', '-i', fname,
                   'output.wav'])
        # Вызов функции для перевода аудио в текст
        result = audio_to_text('output.wav')
        print(result.find('7:00 вечера'))
        # Отправляем пользователю, приславшему файл, его текст
        await bot.send_message(message.from_user.id, format(result))
    except sr.UnknownValueError as e:
        # Ошибка возникает, если сообщение не удалось разобрать. В таком случае отсылается ответ пользователю и заносим запись в лог ошибок
        await bot.send_message(message.from_user.id,  "Прошу прощения, но я не разобрал сообщение, или оно пустое...")
        with open(logfile, 'a', encoding='utf-8') as f:
            f.write(str(datetime.datetime.today().strftime("%H:%M:%S")) + ':' + str(message.from_user.id) + ':' + str(message.from_user.first_name) + '_' +
                    str(message.from_user.last_name) + ':' + str(message.from_user.username) + ':' + str(message.from_user.language_code) + ':Message is empty.\n')
    except Exception as e:
        # В случае возникновения любой другой ошибки, отправляется соответствующее сообщение пользователю и заносится запись в лог ошибок
        await bot.send_message(message.from_user.id,  "Что-то пошло плохо, но наши смелые инженеры уже трудятся над решением... \nДа ладно, никто эту ошибку исправлять не будет, она просто потеряется в логах.")
        with open(logfile, 'a', encoding='utf-8') as f:
            f.write(str(datetime.datetime.today().strftime("%H:%M:%S")) + ':' + str(message.from_user.id) + ':' + str(message.from_user.first_name) + '_' +
                    str(message.from_user.last_name) + ':' + str(message.from_user.username) + ':' + str(message.from_user.language_code) + ':' + str(e) + '\n')
    finally:
        os.remove('output.wav')
        os.remove(fname)


@dp.message_handler()
async def echo_send(message: types.Message):
   if {i.lower() for i in message.text.split(' ')}.intersection(set()) != set():
    await message.reply('Все ок')

executor.start_polling(dp, skip_updates=True, on_startup=on_startup)

data_combinations = {
    '1:00 дня' : '13:00',
    '2:00 дня' : '14:00',
    '3:00 дня' : '15:00',
    '5:00 вечера': '17:00',
    '6:00 вечера': '18:00',
    '7:00 вечера': '19:00',
    '8:00 вечера': '20:00',
    '9:00 вечера': '21:00',
    '10:00 вечера': '22:00',
    '11:00 вечера': '23:00',
    '12:00 ночи': '00:00'
}