import requests
import urllib3
import asyncio
import aiohttp
import string
import datetime
import json
import time as timer
from math import ceil
from bs4 import BeautifulSoup
from flask import Flask, request, abort
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage

# Отключение предупреждения о небезопасном соединении
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Настройка flask
app = Flask(__name__)

# Ключи яндекс
yandex_apikey = "7271aeed-6ae5-46a4-bb1e-71085eec111c"
yandex_apikey_second = "b2c1f321-85a1-4e74-9ef7-5c834e5a074e"

# Настройки бота авито
user_id = '294610886'
client_id = 'jIC1ZsbUkDO_E2FymKEd'
client_secret = 'NceYZWK68aCYctPihLoBnq_7iXOQ0Jfq4nVgx5hq'

# Ключи телеграм
tg_chat_key = '-4078308477'
tg_token = '6393946751:AAE07NC45LCkUF3L7Kwm_vfsr000iBf5SA4'

# Настройки бота телеграм
bot = Bot(tg_token)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

# Массивы
json_messages = []

city_from = ' '
city_to = ' '
prev_inner_message = ' '
endtime = 0
access_granted = False
packing = "Нет"
furniture = "Нет"
trash = "Нет"

promocodes = ["TigersTOP"] # Промокоды пока не вошли в пользование. Предположим, что этот даёт скидку 5%.
greatings_triggers = ["привет","здравствуйте","добрый день","добрый вечер","доброе утро","здорово","здарова","салам","перевозка"]

# Очистка списков
# Перезаполнение списков замедляет работу, поэтому они очищаются каждый раз при новом запуске
async def clear_lists():
    del json_messages[:]    


# Отправка сообщения
async def send_message(access_token, user_id, user_chat_id, message):
    url = f'https://api.avito.ru/messenger/v1/accounts/{user_id}/chats/{user_chat_id}/messages'
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json',
    }
    data = {
        "message": {
        "text": message
        },
        "type": "text"
    }
    response = requests.post(url, headers=headers, data=json.dumps(data))
    if response.status_code == 200:
        print('\nСообщение успешно отправлено\n')
    else:
        print('Ошибка при отправке сообщения:', response)


# Получение и проверка чатов
async def get_messages(access_token, session, user_id, inner_message_type):
    global last_message, user_chat_id, last_message_corrected, user_name, prev_inner_message, first_time_message
    url = f'https://api.avito.ru/messenger/v2/accounts/{user_id}/chats/{user_chat_id}'
    response = await fetch_chat(session, url)
    if response[0]['last_message']['direction'] == 'out':
       return
    elif response[1].status == 200 and response[0]['last_message']['direction'] == 'in':
        global r, json_messages
        json_str = response[0]
        print(f"{timer.strftime('%Y %H:%M:%S', timer.localtime(timer.time()))} ID: {user_chat_id}")
        if inner_message_type == 'text':
          last_message = json_str['last_message']['content']['text']
        elif inner_message_type == 'location':
          last_message = json_str['last_message']['content']['location']['text']
        last_message_id = json_str['last_message']['id']
        print(f"Последнее сообщение: {last_message}")
        last_message_direction = json_str['last_message']['direction']
        print(f"Направление: {last_message_direction}\n")
        last_message_corrected = await remove_punctuation(last_message)
        if last_message_direction == "in":
          user_name = json_str['users'][1]['name']
        elif last_message_direction == "out":
          user_name = json_str['users'][0]['name']
        if inner_message_type == 'text':
          if last_message != json_messages[0]['messages'][0]['content']['text']:
            pass
        elif inner_message_type == 'location':
          if last_message != json_messages[0]['messages'][0]['content']['location']['text']:
            pass
        if last_message_direction == "in":
          # Проверка пишет в первый раз или нет
          x = 0
          first_time_message = ''
          # print(json_messages[x]['messages'])
          while x < len(json_messages[0]['messages']):
            inner_message_direction = json_messages[0]['messages'][x]['direction']
            # print(inner_message_direction)
            inner_message_isRead = json_messages[0]['messages'][x]['isRead']
            # print(f'Read:{inner_message_isRead}')
            if inner_message_direction == 'in' and inner_message_isRead == False:
              first_time_message = True
              inter = await check_intersections(greatings_triggers, last_message_corrected.lower().split())
              if inner_message_direction == 'in' and inter[0].intersection(inter[1]):
                await first_time_message_send(access_token, user_id, user_chat_id)
                break
            elif inner_message_isRead == True:
              first_time_message = False
              break
            x+=1
            
          if first_time_message == False:
            await get_chat_messages(json_messages[0], last_message_direction, access_token, user_id, user_chat_id, inner_message_type)
    else:
        print('Ошибка при получении сообщений:', response)


# Действия если пишет первый раз
async def first_time_message_send(access_token, user_id, user_chat_id):
    await send_message(access_token, user_id, user_chat_id, 'Здравствуйте!\nВы желаете оставить заявку на перевозку? Пришлите мне цифру:\n1. Да\n2. Нет')
    print('Здравствуйте!\nВы желаете оставить заявку на перевозку? Пришлите мне цифру:\n1. Да\n2. Нет')

    # n = 0 
    # while n < len(json_messages['messages']):
    #   inner_message_direction = json_messages['messages'][n]['direction']
    #   inner_message = json_messages['messages'][n]['content']['text']
    #   inner_message_corrected = await remove_punctuation(inner_message)

    #   inter = await check_intersections(greatings_triggers, inner_message_corrected.lower().split())
    #   if inner_message_direction == 'in' and inter[0].intersection(inter[1]):
    #     # await send_message(access_token, user_id, user_chat_id, 'Вы желаете оставить заявку на перевозку?')
    #     print('Вы желаете оставить заявку на перевозку?')
    #   n+=1


# Проверка совпадений в сообщении
async def check_intersections(greatings_triggers, inner_message_corrected):
    s1 = set(inner_message_corrected)
    s2 = set(greatings_triggers)
    return s1, s2


# Получение каждого сообщения в чате
async def get_chat_messages(json_messages, last_message_direction, access_token, user_id, user_chat_id, inner_message_type):
                n = 0 
                while n < len(json_messages['messages']):
                  try:
                    inner_message_direction = json_messages['messages'][n]['direction']
                    if inner_message_type == 'text':
                      inner_message = json_messages['messages'][n]['content']['text']
                    elif inner_message_type == 'location':
                      inner_message = json_messages['messages'][n]['content']['location']['text']
                    inner_message_corrected = await remove_punctuation(inner_message)
                    prev_inner_message = ' '
                    try:
                      prev_inner_message_corrected = ' '
                      prev_inner_message_direction = json_messages['messages'][n+1]['direction']
                      # print(inner_message_corrected)
                      # print(inner_message_direction)
                      try:
                        if prev_inner_message_direction == 'out' and first_time_message == False:
                          prev_inner_message = json_messages['messages'][n+1]['content']['text']
                        else: prev_inner_message = ' '
                        prev_inner_message_corrected = await remove_punctuation(prev_inner_message)
                        if first_time_message == True: prev_inner_message = ' '
                      except: prev_inner_message = ' '
                      print(prev_inner_message_corrected)
                    except IndexError:   
                      prev_inner_message_corrected = ' '
                      pass
                    if last_message_direction == "in":
                      if inner_message_direction == 'in' and prev_inner_message == 'Здравствуйте!\nВы желаете оставить заявку на перевозку? Пришлите мне цифру:\n1. Да\n2. Нет' and 'да' in inner_message_corrected.lower().split() or inner_message_direction == 'in' and prev_inner_message == 'Здравствуйте!\nВы желаете оставить заявку на перевозку? Пришлите мне цифру:\n1. Да\n2. Нет' and '1' in inner_message_corrected.lower().split() or inner_message_direction == 'in' and '2' in inner_message_corrected.lower().split() and prev_inner_message == 'Это правильный адрес погрузки?\n1. Да\n2. Поменять адрес погрузки':
                        await place_start_city(access_token, user_id, user_chat_id)
                        break
                      elif inner_message_direction == 'in' and prev_inner_message == 'Здравствуйте!\nВы желаете оставить заявку на перевозку? Пришлите мне цифру:\n1. Да\n2. Нет' and 'нет' in inner_message_corrected.lower().split() or inner_message_direction == 'in' and prev_inner_message == 'Здравствуйте!\nВы желаете оставить заявку на перевозку? Пришлите мне цифру:\n1. Да\n2. Нет' and '2' in inner_message_corrected.lower().split():
                        await send_message(access_token, user_id, user_chat_id, "Я жду вас в любое время. Не забудьте посетить наш сайт https://tiger-park.ru")
                        break
                      elif inner_message_direction == 'in' and prev_inner_message == "Напишите мне адрес, куда подать машину:\nСоблюдайте шаблон [Город, район(если есть), улица]":
                        await place_start_location(inner_message, access_token, user_id, user_chat_id, 0)
                        break
                      elif inner_message_direction == 'in' and '1' in inner_message_corrected.lower().split() and prev_inner_message == 'Это правильный адрес погрузки? Пришлите мне цифру:\n1. Да\n2. Поменять адрес погрузки' or inner_message_direction == 'in' and '2' in inner_message_corrected.lower().split() and prev_inner_message == 'Это правильный адрес разгрузки?\n1. Да\n2. Поменять адрес разгрузки':
                        await place_finish_city(access_token, user_id, user_chat_id)
                        break
                      elif inner_message_direction == 'in' and prev_inner_message == "Напишите мне адрес, куда отправится машина:\nСоблюдайте шаблон [Город, район(если есть), улица]":
                        await place_finish_location(inner_message, access_token, user_id, user_chat_id, 0)
                        break
                      elif inner_message_direction == 'in' and '1' in inner_message_corrected.lower().split() and prev_inner_message == 'Это правильный адрес разгрузки? Пришлите мне цифру:\n1. Да\n2. Поменять адрес разгрузки':
                        await place_finish_location_check(json_messages['messages'], access_token, user_id, user_chat_id)
                        await rent_time(access_token, user_id, user_chat_id)
                        break
                      elif inner_message_direction == 'in' and prev_inner_message == 'Напишите время аренды в часах (от 1 до 8):':
                        await car_type(access_token, user_id, user_chat_id)  
                        break
                      elif inner_message_direction == 'in' and 'тип машины' in prev_inner_message_corrected.lower():
                        await workers(access_token, user_id, user_chat_id)
                        break
                      elif inner_message_direction == 'in' and 'напишите количество грузчиков' in prev_inner_message_corrected.lower():
                        await date(access_token, user_id, user_chat_id)
                        break
                      elif inner_message_direction == 'in' and 'введите удобную для вас дату' in prev_inner_message_corrected.lower():
                        await time(access_token, user_id, user_chat_id)
                        break
                      elif inner_message_direction == 'in' and 'введите удобное для вас время' in prev_inner_message_corrected.lower():
                        await person(access_token, user_id, user_chat_id)
                        break
                      elif inner_message_direction == 'in' and 'выберите вид лица' in prev_inner_message_corrected.lower():
                        await person_check(inner_message.lower())
                        if person == 'Физическое' or person == 'Не выбрано':
                          await payment_physycal(access_token, user_id, user_chat_id)
                        elif person == 'Юридическое':
                          await payment_legal(access_token, user_id, user_chat_id)
                        break
                      elif inner_message_direction == 'in' and 'выберите вид расчёта' in prev_inner_message_corrected.lower():
                        await phone(access_token, user_id, user_chat_id)
                        break
                      elif inner_message_direction == 'in' and 'ваш номер телефона' in prev_inner_message_corrected.lower():
                        await promocode(access_token, user_id, user_chat_id)
                        break
                      elif inner_message_direction == 'in' and 'введите промокод' in prev_inner_message_corrected.lower():
                        await additional_options(access_token, user_id, user_chat_id, inner_message)
                        break
                      elif inner_message_direction == 'in' and 'доппараметров заказа' in prev_inner_message_corrected.lower():
                        if '1' in inner_message_corrected or '2' in inner_message_corrected or '3' in inner_message_corrected or '4' in inner_message_corrected:
                          await commentary(access_token, user_id, user_chat_id)
                          break
                      elif inner_message_direction == 'in' and 'напишите комментарий' in prev_inner_message_corrected.lower():
                        await check_chat_messages(access_token, user_id, user_chat_id, json_messages)
                        break
                      elif inner_message_direction == 'out' and 'вы уверены в корректности данных' in inner_message_corrected.lower():
                        global order_to_send
                        order_to_send = prev_inner_message
                        if '1' in await remove_punctuation(json_messages['messages'][n-1]['content']['text']) or 'да' in await remove_punctuation(json_messages['messages'][n-1]['content']['text']).lower():
                          await order_send(access_token, user_id, user_chat_id, order_to_send)
                          break
                        elif '2' in await remove_punctuation(json_messages['messages'][n-1]['content']['text']) or 'нет' in await remove_punctuation(json_messages['messages'][n-1]['content']['text']).lower():
                          await place_start_city(access_token, user_id, user_chat_id)
                          break
                        break
                      elif inner_message_direction == 'out' and inner_message == 'Если хотите оставить ещё одну заявку, напишите "Перевозка"':
                        break
                  except KeyError:
                    n+=1
                    pass
                  n+=1


async def check_chat_messages(access_token, user_id, user_chat_id, json_messages):
    global city_from, city_to, first_coord, second_coord, position_start, position_finish
    n = 0
    while n < len(json_messages['messages']):
      inner_message = json_messages['messages'][n]['content']['text']
      if n < (len(json_messages['messages']) - 1):
        prev_inner_message = json_messages['messages'][n+1]['content']['text']
      if 'да' in inner_message.lower() and prev_inner_message == 'Здравствуйте!\nВы желаете оставить заявку на перевозку? Пришлите мне цифру:\n1. Да\n2. Нет':
        k = n-1
        break
      else: k = n
      n+=1
    while k >= 0:
      try:
        inner_message_direction = json_messages['messages'][k]['direction']
        inner_message = json_messages['messages'][k]['content']['text']
        inner_message_corrected = await remove_punctuation(inner_message)
        prev_inner_message = ' '
        try:
          prev_inner_message_corrected = ' '
          prev_inner_message_direction = json_messages['messages'][k+1]['direction']
          # print(inner_message_corrected)
          # print(inner_message_direction)
          try:
            if prev_inner_message_direction == 'out' and first_time_message == False:
              prev_inner_message = json_messages['messages'][k+1]['content']['text']

            else: prev_inner_message = ' '
            prev_inner_message_corrected = await remove_punctuation(prev_inner_message)
            if first_time_message == True: prev_inner_message = ' '
          except: prev_inner_message = ' '
          # print(prev_inner_message_corrected)
        except IndexError:
          # print("IndexError")   
          prev_inner_message_corrected = ' '
          pass
        if inner_message_direction == 'out' and 'Адрес погрузки:' in inner_message:
          position_start = await place_start_location(inner_message.split(':\n')[1], access_token, user_id, user_chat_id, 1)
          print(position_start[0])
          pass
        elif inner_message_direction == 'out' and 'Адрес разгрузки:' in inner_message:
          position_finish = await place_finish_location(inner_message.split(':\n')[1], access_token, user_id, user_chat_id, 1)
          print(position_finish[0])
          pass
        elif inner_message_direction == 'out' and 'расстояние между пунктами погрузки и разгрузки' in inner_message_corrected.lower():
          await distance_check(inner_message)
          pass
        elif inner_message_direction == 'out' and 'время в пути' in inner_message_corrected.lower():
          await time_travel_check(inner_message)
          pass
        elif inner_message_direction == 'in' and prev_inner_message == 'Напишите время аренды в часах (от 1 до 8):':
          await rent_time_check(inner_message)
          print(f'Предполагаемое время аренды: {rent_time}')    
          pass
        elif inner_message_direction == 'in' and 'тип машины' in prev_inner_message_corrected.lower():
          await car_type_check(inner_message.lower())
          print(f'Тип машины: {car_type}')  
          pass
        elif inner_message_direction == 'in' and 'напишите количество грузчиков' in prev_inner_message_corrected.lower():
          await workers_check(inner_message)
          print(f'Количество грузчиков: {workers}')
          pass
        elif inner_message_direction == 'in' and 'введите удобную для вас дату' in prev_inner_message_corrected.lower():
          await date_check(inner_message.lower())
          pass
        elif inner_message_direction == 'in' and 'введите удобное для вас время' in prev_inner_message_corrected.lower():
          await time_check(inner_message.lower())
          print(f'Время: {time}')
          pass
        elif inner_message_direction == 'in' and 'выберите вид лица' in prev_inner_message_corrected.lower():
          await person_check(inner_message.lower())
          print(f'Вид лица: {person}')
          pass
        elif inner_message_direction == 'in' and prev_inner_message == 'Выберите вид расчёта. Пришлите мне цифру:\n1. Наличный\n2. Картой или по СБП':
          await payment_physycal_check(inner_message.lower())
          print(f'Вид расчёта: {payment}')
          pass
        elif inner_message_direction == 'in' and prev_inner_message == 'Выберите вид расчёта. Пришлите мне цифру:\n1. Оплата на расчетный счет\n2. Безналичный расчет без НДС\n3. Безналичный расчет c НДС':
          await payment_legal_check(inner_message.lower())
          print(f'Вид расчёта: {payment}')
          pass
        elif inner_message_direction == 'in' and 'ваш номер телефона' in prev_inner_message_corrected.lower():
          await phone_check(inner_message)
          print(f'Номер телефона: {phone}')
          pass
        elif inner_message_direction == 'in' and 'введите промокод' in prev_inner_message_corrected.lower():
          await promocode_check(inner_message)
          print(f'Промокод: {promocode}')
          pass
        elif inner_message_direction == 'in' and 'доппараметров заказа' in prev_inner_message_corrected.lower():
          await options_check(inner_message.lower())
          pass
        elif inner_message_direction == 'in' and 'комментарий' in prev_inner_message_corrected.lower():
          await commentary_check(inner_message.lower())
          await order_summary()
          await order_confirm(access_token, user_id, user_chat_id)
      except KeyError:
        k-=1
        pass
      k-=1


# Удаление знаков пунктуации
async def remove_punctuation(input_string):
    # Заставляем транслятор убирать знаки пунктуации
    translator = str.maketrans('', '', string.punctuation)
    # Используем транслятор
    return input_string.translate(translator)


# Получение access_token
async def get_access_token():
    global access_token, token_expire_time
    url = 'https://api.avito.ru/token'
    data = {
        'grant_type': 'client_credentials',
        'client_id': client_id,
        'client_secret': client_secret,
    }
    response = requests.post(url, data=data)
    if response.status_code == 200:
        access_token = response.json()['access_token']
        token_expire_time = response.json()['expires_in']
        print(f'Авторизация прошла успешно\n\n{response.json()}\n')
    else:
        print('Ошибка при авторизации:', response.text)


# Получение всех результатов запросов
async def fetch_all(url):
    global user_chat_id
    print("-------------------------------------------")
    print(f"Starting fetch at: {timer.strftime('%Y %H:%M:%S', timer.localtime(timer.time()))}")
    # print(f"Access token expires in {token_expire_time} seconds")
    try:
      async with aiohttp.ClientSession() as session:
          await fetch_messages(session, url)
      # break
    except ConnectionRefusedError: return 'NOT OK'
    print(f"Ending fetch at:   {timer.strftime('%Y %H:%M:%S', timer.localtime(timer.time()))}")
    print("-------------------------------------------\n")
    return 'OK'


# Получаем список чатов
async def fetch_chat(session, url):
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json',
        }
    async with session.get(url, headers=headers) as response:
        return await response.json(), response


# Получаем список сообщений
async def fetch_messages(session, url):
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json',
        }
    async with session.get(url, headers=headers) as r:
      resp = await r.json()
      json_messages.append(resp)
      # print(json_messages)
    return 'OK'


# Основа кода
@app.route('/', methods=['POST'])
async def main():
    global access_granted, endtime, access_token, user_chat_id
    if request.method == 'POST' and request.json['payload']['value']['type'] == 'text' or request.method == 'POST' and request.json['payload']['value']['type'] == 'location':
        await clear_lists()
        if access_granted == False or timer.time() > endtime:
          endtime = timer.time() + 70
          await get_access_token()
          access_granted = True
        inner_message_type = request.json['payload']['value']['type']
        # if inner_message_type == 'text':
        #   inner_message = request.json['payload']['value']['content']['text']
        # elif inner_message_type == 'location':
        #   inner_message = request.json['payload']['value']['content']['location']['text']
        # inner_message_id = request.json['payload']['value']['id']
        user_chat_id = request.json['payload']['value']['chat_id']
        await fetch_all(f'https://api.avito.ru/messenger/v3/accounts/{user_id}/chats/{user_chat_id}/messages/')
        async with aiohttp.ClientSession() as session:
          await get_messages(access_token, session, user_id, inner_message_type)

        return 'success', 200
    else:
        abort(400)


# Запрос адреса погрузки
async def place_start_city(access_token, user_id, user_chat_id):
    # if last_message.lower() == "да" or message.text.lower() == "поменять адрес погрузки":
    await send_message(access_token, user_id, user_chat_id, "Напишите мне адрес, куда подать машину:\nСоблюдайте шаблон 'Город, район(если есть), улица'")
    # elif message.text.lower() == "назад":
    #   # Возврат к началу
    #   return
    # else:
    #   await message.answer(
    #     text="Я не знаю такой команды😢. Выберите команду из списка выше☝️")


# Проверка адреса погрузки
async def place_start_location(inner_message, access_token, user_id, user_chat_id, check):
    global first_address, first_coord, city_from
    coord = inner_message
    r = requests.get(f'https://geocode-maps.yandex.ru/1.x/?apikey={yandex_apikey}&format=json&geocode={coord}&kind=house')
    if len(r.json()['response']['GeoObjectCollection']['featureMember']) > 0:
      coords = r.json()['response']['GeoObjectCollection']['featureMember'][0][
          'GeoObject']['Point']['pos']
      address = r.json()['response']['GeoObjectCollection']['featureMember'][
          0]['GeoObject']['metaDataProperty']['GeocoderMetaData']['text']
      first_address = address
      first_coord = coords
      if check == 0:
        await send_message(access_token, user_id, user_chat_id, f'Адрес погрузки:\n{first_address}')
        await send_message(access_token, user_id, user_chat_id, 'Это правильный адрес погрузки?\n1. Да\n2. Поменять адрес погрузки')
      if "Республика" in address.split(", ")[1]:
        city_from = address.split(", ")[2]
      elif "Республика" not in address.split(", ")[1]:
        city_from = address.split(", ")[1]
    else:
      await send_message(access_token, user_id, user_chat_id, 'Не удалось получить Ваш адрес')
      await place_start_city(access_token, user_id, user_chat_id)
    return first_address, city_from, first_coord


# Запрос адреса разгрузки
async def place_finish_city(access_token, user_id, user_chat_id):
  await send_message(access_token, user_id, user_chat_id, "Напишите мне адрес, куда отправится машина:\nСоблюдайте шаблон 'Город, район(если есть), улица'")


# Проверка адреса разгрузки
async def place_finish_location(inner_message, access_token, user_id, user_chat_id, check):
    global second_address, second_coord, city_to
    coord = inner_message
    r = requests.get(f'https://geocode-maps.yandex.ru/1.x/?apikey={yandex_apikey}&format=json&geocode={coord}&kind=house')
    if len(r.json()['response']['GeoObjectCollection']['featureMember']) > 0:
      coords = r.json()['response']['GeoObjectCollection']['featureMember'][0][
          'GeoObject']['Point']['pos']
      address = r.json()['response']['GeoObjectCollection']['featureMember'][
          0]['GeoObject']['metaDataProperty']['GeocoderMetaData']['text']
      second_address = address
      second_coord = coords
      if check == 0:
        await send_message(access_token, user_id, user_chat_id, f'Адрес разгрузки:\n{second_address}')
        await send_message(access_token, user_id, user_chat_id, 'Это правильный адрес разгрузки?\n1. Да\n2. Поменять адрес разгрузки')
      if "Республика" in address.split(", ")[1]:
        city_to = address.split(", ")[2]
      elif "Республика" not in address.split(", ")[1]:
        city_to = address.split(", ")[1]
    else:
      await send_message(access_token, user_id, user_chat_id, 'Не удалось получить Ваш адрес')
      await place_finish_city(access_token, user_id, user_chat_id)
    return second_address, city_to, second_coord


# Проверка адреса разгрузки
async def place_finish_location_check(json_messages, access_token, user_id, user_chat_id):
    global first_coord, second_coord
    k = len(json_messages) - 1
    while k >= 0:
      inner_message_direction = json_messages[k]['direction']
      inner_message = json_messages[k]['content']['text']
      if inner_message_direction == 'out' and 'Адрес погрузки' in inner_message:
        first_coord = await place_start_location(inner_message.split(':\n')[1], access_token, user_id, user_chat_id, 1)
      elif inner_message_direction == 'out' and 'Адрес разгрузки' in inner_message:
        second_coord = await place_finish_location(inner_message.split(':\n')[1], access_token, user_id, user_chat_id, 1)
      k-=1

    url = f'https://api-maps.yandex.ru/2.0/?apikey={yandex_apikey_second}&lang=ru_RU'
    r = requests.get(url)
    soup_distance = BeautifulSoup(r.text, 'html.parser')
    token = str(soup_distance).split('"')[15]
    print(token)
    url = f'https://api-maps.yandex.ru/services/route/2.0/?callback=id_1691434615276486510711&lang=ru_RU&token={token}&rll={str(first_coord[2]).split(" ")[0]}%2C{str(first_coord[2]).split(" ")[1]}~{str(second_coord[2]).split(" ")[0]}%2C{str(second_coord[2]).split(" ")[1]}&rtm=atm&results=1&apikey={yandex_apikey_second}'
    r = requests.get(url)
    soup_distance = BeautifulSoup(r.text, 'html.parser')
    print(soup_distance)
    try:
      distances = str(soup_distance).split('"')[43]
      time_travel = str(soup_distance).split('"')[51]
      await send_message(access_token, user_id, user_chat_id, f'Расстояние между пунктами погрузки и разгрузки: {distances}')
      await send_message(access_token, user_id, user_chat_id, f'Предполагаемое время в пути: {time_travel}')
    except IndexError:
      pass
    # distances = str(soup_distance).split('"')[43]
    # time_travel = str(soup_distance).split('"')[51]
    # print(f'Расстояние между пунктами погрузки и разгрузки: {distances}')
    # print(f'Предполагаемое время в пути: {time_travel}')
    # await send_message(access_token, user_id, user_chat_id, f'Расстояние между пунктами погрузки и разгрузки: {distances}')
    # await send_message(access_token, user_id, user_chat_id, f'Предполагаемое время в пути: {time_travel}')


# Проверка расстояния между адресами
async def distance_check(inner_message):
    global distances
    distances = inner_message.split(': ')[1]
    print(f'Расстояние между пунктами погрузки и разгрузки: {distances}')


# Проверка времени в пути
async def time_travel_check(inner_message):
    global time_travel
    time_travel = inner_message.split(': ')[1]
    print(f'Предполагаемое время в пути: {time_travel}')


# Округление времени с шагом 0.5
async def round_off_rating(number):
    return ceil(number * 2) / 2


# Запрос времени аренды машины
async def rent_time(access_token, user_id, user_chat_id):
    await send_message(access_token, user_id, user_chat_id, 'Напишите время аренды в часах (от 1 до 8):')


# Проверка времени аренды машины
async def rent_time_check(inner_message):
    global rent_time
    if inner_message.isdigit() == True and inner_message.isdigit() >= 1 and inner_message.isdigit() <= 8:
      inner_message = inner_message.replace(",", ".")
      rent_time = await round_off_rating(float(inner_message))


# Запрос типа машины
async def car_type(access_token, user_id, user_chat_id):
    await send_message(access_token, user_id, user_chat_id, 'Выберите тип машины. Пришлите мне цифру:\n1. Любая Газель\n2. Бортовая Газель\n3. Газель Пирамида\n4. Газель фургон 3м\n5. Газель фургон 4м\n6. Газель фургон 5м\n7. Грузовик свыше 1.5 тонн\n8. Грузовик свыше 5 тонн\n9. Нужна помощь\n10. Грузчики без машины')


# Проверка типа машины
async def car_type_check(inner_message):
    global car_type
    if inner_message.isdigit() == True and inner_message.isdigit() >= 1 and inner_message.isdigit() <= 10:
      match inner_message:
        case '1': car_type = 'Любая Газель'
        case '2': car_type = 'Бортовая Газель'
        case '3': car_type = 'Газель Пирамида'
        case '4': car_type = 'Газель фургон 3м'
        case '5': car_type = 'Газель фургон 4м'
        case '6': car_type = 'Газель фургон 5м'
        case '7': car_type = 'Грузовик свыше 1.5 тонн'
        case '8': car_type = 'Грузовик свыше 5 тонн'
        case '9': car_type = 'Нужна помощь'
        case '10': car_type = 'Грузчики без машины'
        case 'любая газель': car_type = 'Любая Газель'
        case 'любая': car_type = 'Любая Газель'
        case 'бортовая газель': car_type = 'Бортовая Газель'
        case 'газель пирамида': car_type = 'Газель Пирамида'
        case 'газель фургон 3м': car_type = 'Газель фургон 3м'
        case 'газель фургон 4м': car_type = 'Газель фургон 4м'
        case 'газель фургон 5м': car_type = 'Газель фургон 5м'
        case 'грузовик свыше 1.5 тонн': car_type = 'Грузовик свыше 1.5 тонн'
        case 'грузовик свыше 5 тонн': car_type = 'Грузовик свыше 5 тонн'
        case 'нужна помощь': car_type = 'Нужна помощь'
        case 'грузчики без машины': car_type = 'Грузчики без машины'
        case 'без машины': car_type = 'Грузчики без машины'
        case 'только грузчики': car_type = 'Грузчики без машины'
        case _: car_type = 'Любая Газель'


# Запрос количества грузчиков
async def workers(access_token, user_id, user_chat_id):
    await send_message(access_token, user_id, user_chat_id, 'Напишите количество грузчиков. Пришлите мне цифру:\n0. Машина без грузчиков')


# Проверка количества грузчиков
async def workers_check(inner_message):
    global workers
    if inner_message.isdigit() == True and inner_message.isdigit() >= 1:
      workers = inner_message
    elif inner_message.isdigit() == True and inner_message.isdigit() == 0:
      workers = 'Машина без грузчиков'


# Запрос даты
async def date(access_token, user_id, user_chat_id):
    today = datetime.date.today()
    tomorrow = today + datetime.timedelta(days=1)
    after_tomorrow = today + datetime.timedelta(days=2)
    await send_message(access_token, user_id, user_chat_id, f"Введите удобную для вас дату. Пришлите цифру или напишите сами:\n1. Сегодня ({today.strftime('%d.%m')})\n2. Завтра ({tomorrow.strftime('%d.%m')})\n3. Послезавтра ({after_tomorrow.strftime('%d.%m')})\n4. Выберите за меня (скидка 10-25%)\n5. Пропустить\n\nОпция 'Выберите за меня' — мы сами назначим вам удобное для нас время.\n\nЗаказ после 20:00, оформляется заранее.")


# Проверка даты
async def date_check(inner_message):
  global date
  today = datetime.date.today()
  tomorrow = today + datetime.timedelta(days=1)
  after_tomorrow = today + datetime.timedelta(days=2)
  match inner_message:
    case '1': date = f"Сегодня ({today.strftime('%d.%m')})"
    case '2': date = f"Завтра ({tomorrow.strftime('%d.%m')})"
    case '3': date = f"Послезавтра ({after_tomorrow.strftime('%d.%m')})" 
    case '4': date = "Опция 'Выберите за меня'"
    case '5': date = "Не выбрано"
    case 'сегодня': date = f"Сегодня ({today.strftime('%d.%m')})"
    case 'завтра': date = f"Завтра ({tomorrow.strftime('%d.%m')})"
    case 'послезавтра': date = f"Послезавтра ({after_tomorrow.strftime('%d.%m')})" 
    case 'выберите за меня': date = "Опция 'Выберите за меня'"
    case 'пропустить': date = "Не выбрано"
    case _: date = inner_message
  print(f'Дата: {date}')


# Запрос времени
async def time(access_token, user_id, user_chat_id):
    await send_message(access_token, user_id, user_chat_id, "Введите удобное для вас время или пришлите мне цифру:\n1. Мне не срочно (скидка 15%)\n2. Пропустить\n\nОпция 'Мне не срочно' — скидка 15% при заказе в определённые временные интервалы.")


# Проверка времени
async def time_check(inner_message):
    global time
    match inner_message:
      case '1': time = "Опция 'Мне не срочно'"
      case '2': time = "Не выбрано"
      case 'не срочно': time = "Опция 'Мне не срочно'"
      case 'мне не срочно': time = "Опция 'Мне не срочно'"
      case 'пропустить': time = "Не выбрано"
      case _: time = inner_message


# Запрос вида лица
async def person(access_token, user_id, user_chat_id):
    await send_message(access_token, user_id, user_chat_id, 'Выберите вид лица. Пришлите мне цифру:\n1. Физическое\n2. Юридическое')


# Проверка вида лица
async def person_check(inner_message):
    global person
    match inner_message:
      case '1': person = 'Физическое'
      case '2': person = 'Юридическое'
      case 'физическое': person = 'Физическое'
      case 'юридическое': person = 'Юридическое'
      case 'физ': person = 'Физическое'
      case 'юр': person = 'Юридическое'
      case _: person = 'Не выбрано'

# Запрос вида оплаты для физ.лица
async def payment_physycal(access_token, user_id, user_chat_id):
    await send_message(access_token, user_id, user_chat_id, 'Выберите вид расчёта. Пришлите мне цифру:\n1. Наличный\n2. Картой или по СБП')


# Запрос вида оплаты для юр.лица
async def payment_legal(access_token, user_id, user_chat_id):
    await send_message(access_token, user_id, user_chat_id, 'Выберите вид расчёта. Пришлите мне цифру:\n1. Оплата на расчетный счет\n2. Безналичный расчет без НДС\n3. Безналичный расчет c НДС')


# Проверка вида оплаты физ.лица
async def payment_physycal_check(inner_message):
    global payment
    match inner_message:
      case '1': payment = 'Наличный'
      case '2': payment = 'Картой или по СБП'
      case 'наличный': payment = 'Наличный'
      case 'наличка': payment = 'Наличный'
      case 'картой': payment = 'Картой или по СБП'
      case 'карта': payment = 'Картой или по СБП'
      case _: payment = 'Не выбрано'
       

# Проверка вида оплаты юр.лица
async def payment_legal_check(inner_message):
    global payment
    match inner_message:
      case '1': payment = 'Оплата на расчетный счет'
      case '2': payment = 'Безналичный расчет без НДС'
      case '3': payment = 'Безналичный расчет c НДС'
      case 'расчетный счет': payment = 'Оплата на расчетный счет'
      case 'оплата на расчетный счет': payment = 'Оплата на расчетный счет'
      case 'безналичный расчет без ндс': payment = 'Безналичный расчет без НДС'
      case 'безналичный расчет c ндс': payment = 'Безналичный расчет c НДС'
      case 'без ндс': payment = 'Безналичный расчет без НДС'
      case 'c ндс': payment = 'Безналичный расчет c НДС'
      case _: payment = 'Не выбрано'


# Запрос номера телефона
async def phone(access_token, user_id, user_chat_id):
    await send_message(access_token, user_id, user_chat_id, 'Для связи с вами нам необходим ваш номер телефона📞')


# Запись номера
async def phone_check(inner_message):
    global phone
    phone = inner_message


# Запрос промокода
async def promocode(access_token, user_id, user_chat_id):
    await send_message(access_token, user_id, user_chat_id, 'Введите промокод. Пришлите мне цифру:\n1. У меня нет промокода')


# Проверка промокода
async def promocode_check(inner_message):
    global promocode
    match inner_message:
      case '1': promocode = 'Не выбрано'
      case 'нет промокода': promocode = 'Не выбрано'
      case _: promocode = inner_message


# Запрос доп.опций
async def additional_options(access_token, user_id, user_chat_id, inner_message):
    if inner_message in promocodes or inner_message == '1':
      await send_message(access_token, user_id, user_chat_id, 'Выберите один или несколько доп.параметров заказа (слитно, в строчку). Пришлите мне цифру:\n1. Упаковка\n2. Разборка мебели\n3. Вывоз хлама\n4. Мне ничего не нужно')
    else:
      await send_message(access_token, user_id, user_chat_id, 'Неверный промокод')
      await promocode(access_token, user_id, user_chat_id)


# Проверка опций
async def options_check(inner_message):
    global packing, furniture, trash
    inner_message = list(inner_message)
    if '1' in inner_message or '2' in inner_message or '3' in inner_message or '4' in inner_message:
      match inner_message:
        case '1': packing = "Да"
        case '2': furniture = "Да"
        case '3': trash = "Да"
        case '4':
          packing = "Нет"
          furniture = "Нет"
          trash = "Нет"
        case 'упаковка': packing = "Да"
        case 'разборка мебели': furniture = "Да"
        case 'разбор мебели': furniture = "Да"
        case 'вывоз хлама': trash = "Да"
        case 'мне ничего не нужно':
          packing = "Нет"
          furniture = "Нет"
          trash = "Нет"
        case 'ничего не нужно':
          packing = "Нет"
          furniture = "Нет"
          trash = "Нет"
      print(f'Выбрано {inner_message} Доп.параметры заказа: {packing}, {furniture}, {trash}')


# Запрос комментария
async def commentary(access_token, user_id, user_chat_id):
    await send_message(access_token, user_id, user_chat_id, 'Напишите комментарий к заказу:\n1. Пропустить')


# Проверка комментария
async def commentary_check(inner_message):
    global commentary_order
    match inner_message:
      case '1': commentary_order = 'Без комментария'
      case 'пропустить': commentary_order = 'Без комментария'
      case _: commentary_order = inner_message
    print(f'Комментарий: {commentary_order}')


# Расчёт стоимости
async def order_summary():
    global price
    # Запрос расчёта на сайт
    url = f'https://v1.tiger-park-api.ru/api/v1/get/price?to={position_finish[1]}&time={rent_time}&workersNumber={workers}'
    r = requests.get(url, verify=False)
    soup = BeautifulSoup(r.content, 'html.parser')
    if promocode == "TigersTOP":
      price = float(str(soup)) * 0.95
    else:
      price = soup


# Подтверждение заказа
async def order_confirm(access_token, user_id, user_chat_id):


    await send_message(access_token, user_id, user_chat_id, 'Ваш заказ:')
    await send_message(access_token, user_id, user_chat_id, f"Основная информация:\nИмя клиента: {user_name}\nТелефон клиента: {phone}\n{position_start[0]}\n{position_finish[0]}\nЖелаемая дата: {date}\nЖелаемое время: {time}\nТип машины: {car_type}\n\nДополнительная информация:\nКол-во грузчиков: {workers} чел.\nВремя аренды: {rent_time} ч.\nРасстояние между пунктами погрузки и разгрузки: {distances}\nВид лица: {person}\nВид расчёта: {payment}\nКомментарий к заказу: {commentary_order}\nПромокод: {promocode}\n\nДополнительные параметры заказа:\n-Упаковка: {packing}\n-Разборка мебели: {furniture}\n-Вывоз хлама: {trash}\n\nСтоимость заказа от: {price} руб.\n")
    await send_message(access_token, user_id, user_chat_id, 'Вы уверены в корректности данных? Пришлите мне цифру:\n1. Да, подтвердить заказ\n2. Нет, заполнить заново')
    # print(f"\nВаш заказ:\n\nОсновная информация:\nИмя клиента: {user_name}\nТелефон клиента: {phone}\n{position_start[0]}\n{position_finish[0]}\nЖелаемая дата: {date}\nЖелаемое время: {time}\nТип машины: {car_type}\n\nДополнительная информация:\nКол-во грузчиков: {workers} чел.\nВремя аренды: {rent_time} ч.\nРасстояние между пунктами погрузки и разгрузки: {distances}\nВид лица: {person}\nВид расчёта: {payment}\nКомментарий к заказу: {commentary_order}\nПромокод: {promocode}\n\nДополнительные параметры заказа:\n-Упаковка: {packing}\n-Разборка мебели: {furniture}\n-Вывоз хлама: {trash}\n\nСтоимость заказа от: {price} руб.\n")
    # print("Вы уверены в корректности данных?\n1. Да, подтвердить заказ\n2. Нет, заполнить заново")


# Отправка заказа в чат
async def order_send(access_token, user_id, user_chat_id, order_to_send):
  msg_to_chat = await bot.send_message(tg_chat_key,
                                       order_to_send,
                                       reply_markup=None)
  await send_message(access_token, user_id, user_chat_id, 'Спасибо за ваш заказ🐯! Мы с вами скоро свяжемся📞!')
  await send_message(access_token, user_id, user_chat_id, 'Если хотите оставить ещё одну заявку, напишите "Перевозка"')
  markup_inline = types.InlineKeyboardMarkup()
  item1 = types.InlineKeyboardButton("Принять", callback_data="order_accept")
  markup_inline.add(item1)
  await bot.edit_message_text(chat_id=tg_chat_key,
                              message_id=msg_to_chat.message_id,
                              text='🆕<b>Новый заказ из Авито!</b>🆕\n\n' +
                              order_to_send,
                              parse_mode='html',
                              reply_markup=markup_inline)


# # Принятие заказа в лс
# @dp.callback_query_handler(text="order_accept")
# async def order_accept(call: types.CallbackQuery):
#   markup_inline = types.InlineKeyboardMarkup()
#   item1 = types.InlineKeyboardButton("Закрыть заказ",
#                                      callback_data="order_close")
#   markup_inline.add(item1)
#   await bot.send_message(call.from_user.id,
#                                           call.message.text,
#                                           reply_markup=markup_inline)
#   call.message.text = call.message.text.replace('🆕Новый заказ из бота!🆕',
#                                                 '✔Заказ принят✔')
#   await call.message.edit_text(text=call.message.text)


# # Закрытие заказа
# @dp.callback_query_handler(text="order_close")
# async def order_close(call: types.CallbackQuery):
#   call.message.text = call.message.text.replace('🆕Новый заказ из бота!🆕',
#                                                 '❌Заказ закрыт!❌')
#   await call.message.edit_text(text=call.message.text)

# app.run()
# try:
#   loop = asyncio.get_running_loop()
# except RuntimeError:
#   loop = asyncio.new_event_loop()
# asyncio.set_event_loop(loop)
# loop.run_forever()
  
if __name__ == '__main__':
  app.run(use_reloader=False)          