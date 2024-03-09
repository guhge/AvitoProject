import requests
import json

# Настройки бота авито
user_id = '294610886'
client_id = 'jIC1ZsbUkDO_E2FymKEd'
client_secret = 'NceYZWK68aCYctPihLoBnq_7iXOQ0Jfq4nVgx5hq'

webhook_url_old = 'https://8782-78-30-242-38.ngrok-free.app'
webhook_url = 'https://5bb2-78-30-242-38.ngrok-free.app'

# Получение access_token
def get_access_token():
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

def delete_webhook():
    url = f'https://api.avito.ru/messenger/v3/webhook/unsubscribe'
    print(url)
    data = {
        'url': webhook_url_old
    }
    headers = {
    'Authorization': f'Bearer {access_token}',
    'Content-Type': 'application/json'
    }
    r = requests.post(url, json=data, headers=headers)
    try:
        print(r.json())
    except: return

def update_webhook():
    url = f'https://api.avito.ru/messenger/v3/webhook'
    print(url)
    data = {
        'url': webhook_url
    }
    headers = {
    'Authorization': f'Bearer {access_token}',
    'Content-Type': 'application/json'
    }
    r = requests.post(url, json=data, headers=headers)
    try:
        print(r.json())
    except: return

def get_reviews():
    url = f'https://api.avito.ru/ratings/v1/reviews'
    print(url)
    params = {
        'offset': 0,
        'limit': 2
    }
    headers = {
    'Authorization': f'Bearer {access_token}',
    'Content-Type': 'application/json'
    }
    r = requests.get(url, params=params, headers=headers)
    try:
        print(r.json())
        # print(r.json()[])
    except: return


# data = {
#     'name': 'Michael',
#     'Adress': 'Sevastopol'
# }

# r = requests.post(webhook_url, data=json.dumps(data), headers={'Content-Type': 'application/json'})
# r = requests.post(webhook_url, data=json.dumps(data), headers={'Content-Type': 'application/json'})
# print(r)

get_access_token()
# get_reviews()
delete_webhook()
update_webhook()
