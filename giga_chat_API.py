import base64
import requests
import uuid
import json

###  ключ тут   ###
api_key = 'Y2I1ODNmN2UtYTgwYS00ZmY4LWI3OGUtNjVlMzM2NmMwODdlOjRmNDRiYjI0LTVhOTktNDYzZC05MWUxLTU3YmRiNzQzN2I2Mw=='
base64_credentials = base64.b64encode(api_key.encode('utf-8')).decode('utf-8')   #если не получится убери utf


#получение ответа на запрос пользователя
#возвращает ответ от api в виде текстовой строки
def get_chat(giga_token, user_message):
    #URL API
    url = 'https://gigachat.devices.sberbank.ru/api/v1/chat/completions'
    #подготовка запроса в json
    payload = json.dumps({
        "model": "GigaChat",
        "messages": [
            {
                "role": "user", #роль отправителя
                "content": user_message #содержание сообщения
            }
        ],
        "temperature": 1, #температура генерации(насколько ответ случайный)(чем больше параметр, тем случайнее ответ)
        "top_p": 0.1, #контроль разнообразия
        "n": 1, #количество возвращаемых ответов
        "stream": False, #потоковая ли передача(если ставим тру, то мы будем видеть генерацию ответа)
        "max_token": 512, #максимальное количество токенов
        "repetition_penalty": 1, #штраф за повторения
        "update_interval": 0 #интервал потоковой пердачи
    })

    #заголовки запрроса
    headers = {
        "Content-Type": 'application/json', #тип содержимого json
        "Accept": 'application/json', #получаем json
        "Authorization" : f"Bearer {giga_token}"
    }
    #Выполнение  POST запроса и получение ответа
    try:
        response = requests.request("POST", url, headers=headers, data=payload, verify=False)
        return response
    except requests.RequestException as e:
        print(f'error {e}')
        return -1



#получение временного токена
def get_token(base64_credentials):
    #создание индентификатора UUID
    rq_uid = str(uuid.uuid4())

    #API URL
    url = 'https://ngw.devices.sberbank.ru:9443/api/v2/oauth'

    #заголовки
    headers = {'Content-Type': 'application/x-www-form-urlencoded',
           'Accept': 'application/json',
           'RqUID': rq_uid,
           'Authorization': f"Basic {base64_credentials}"
        }

    #тело запроса
    payload={
           'scope': 'GIGACHAT_API_PERS'
         }
    try:
         #Делаем post запрос
         response = requests.post(url, headers=headers, data=payload, verify=False)
         return response
    except requests.RequestException as e:
        print(f'error {e}')
        return -1
def cafe(cafe, place, giga_token):
    prompt = f"Привет, помоги мне пожалуйста. Представь себя Экспертом по кафе и ресторанам в Москве, и расскажи какие {cafe} в районе {place} есть. Выведи 3 варианта в виде 'Название Кафе' : 'Небольшое описание буквально в 50 слов' ."
    answer = get_chat(giga_token, prompt)
    return answer.json()['choices'][0]['message']['content']


response = get_token(api_key)
if response != 1:
    print(response.text)
    giga_token = response.json()["access_token"]

'''
#получение списка доспупных моделей
url = 'https://gigachat.devices.sberbank.ru/api/v1/models'

payload = {}
headers = {
    'Accept': 'application/json',
    'Authorization': f"Bearer {giga_token}"
}

response = requests.request("GET", url, headers=headers, data=payload, verify=False)
print(response.text)
'''
### получение ключевых слов по категориям ###
message = '«Привет! Я хочу прогуляться по Москве с друзьями! У меня есть всего 3 часа. Хочу зайти во французское кафе, пройтись по старому Арбату, Москва-сити и придти к метро  беблиотека им ленина.» Найди ключевые слова и раздели их по категориям: город, где поесть, метро, время, место. Напиши мне только слова разделенные по категориям'
answer = get_chat(giga_token, message)
print(answer.json())
print(answer.json()['choices'][0]['message']['content'])
data_general = {}
data_key = 'Город, Где поесть, Метро, Время, Место'.split(', ')
for i in answer.json()['choices'][0]['message']['content'].split('\n'):
    s = i.split(': ')
    value = s[1].split(', ')
    data_general[s[0]] = value
print(data_general)


### получение интересных мест ###
places = ', '.join(data_general['Место'])
prompt_data = f"Привет, представь себя экскурсоводом-экспертом по Москве и помоги мне пожалуйста . У меня есть различные места: {places} и тебе нужно сказать мне, что конкретно там можно интересного посмотреть (от 1 до 3 объектов интереса) . Выведи в формате 'Место':'Объект инетереса', начало каждого пункта обозначь - "
answer = get_chat(giga_token, prompt_data)
print(answer.json())
data_places_interest = {}
for i in answer.json()['choices'][0]['message']['content'].split('\n\n'):
    i = i.split(':\n')
    data_places_interest[i[0].strip(':')] = i[1].strip('-').split(';\n- ')
print(data_places_interest)


### получение кафешек в районе ###
if 'Где поесть' in data_general.keys():
    answer = cafe(data_general['Где поесть'], data_general['Место'], giga_token)
    print(answer)

