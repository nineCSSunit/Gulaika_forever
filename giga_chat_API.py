import requests
import uuid
import json
import time
import urllib3


urllib3.disable_warnings()


####################################################       Считывание конфигурационного файла      ####################


with open("config.json") as config_file:
    config = json.load(config_file)

GIGACHAT_API_KEY = config["GIGACHAT_API_KEY"]

####################################################       Нейронки         ############################################

"""
###  Кодируем ключ тут   ###

base64_credentials = base64.b64encode(GIGACHAT_API_KEY.encode('utf-8')).decode('utf-8')   #если не получится убери utf

"""


#                                       получение временного токена
def get_token(base64_credentials):
    #                            создание индентификатора UUID
    rq_uid = str(uuid.uuid4())

    #                   API URL
    url = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"

    #                 заголовки
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/json",
        "RqUID": rq_uid,
        "Authorization": f"Basic {base64_credentials}",
    }

    #               тело запроса
    payload = {"scope": "GIGACHAT_API_PERS"}
    try:
        #           Делаем post запрос
        response = requests.post(url, headers=headers, data=payload, verify=False)
        return response
    except requests.RequestException as e:
        print(f"error {e}")
        return -1



# Глобальные переменные для хранения токена и времени его истечения
giga_token = None
token_expires_at = 0  # Время истечения токена в секундах

# Функция для получения действующего токена
def get_valid_token(api_key):
    global giga_token, token_expires_at
    current_time = time.time()
    # Проверяем, истек ли токен
    if giga_token is None or current_time >= token_expires_at:
        print("Токен истек или не существует. Обновляем токен...")
        response = get_token(api_key)
        if response != 1:
            giga_token = response.json().get("access_token")
            token_expires_at = response.json().get("expires_at")  # Время истечения в секундах
            return giga_token
        else:
            print("Ошибка при получении токена")
            return None
    return giga_token






#     получение ответа на запрос пользователя
#       возвращает ответ от api в виде текстовой строки

def get_chat(user_message):
    get_valid_token(GIGACHAT_API_KEY)
    #          URL API
    url = "https://gigachat.devices.sberbank.ru/api/v1/chat/completions"
    #          подготовка запроса в json
    payload = json.dumps(
        {
            "model": "GigaChat",
            "messages": [
                {
                    "role": "user",  #             роль отправителя
                    "content": user_message,  #           содержание сообщения
                }
            ],
            "temperature": 1,  # температура генерации(насколько ответ случайный)(чем больше параметр, тем случайнее ответ)
            "top_p": 0.1,  # контроль разнообразия
            "n": 1,  # количество возвращаемых ответов
            "stream": False,  # потоковая ли передача(если ставим тру, то мы будем видеть генерацию ответа)
            "max_token": 512,  # максимальное количество токенов
            "repetition_penalty": 1,  # штраф за повторения
            "update_interval": 0,  # интервал потоковой пердачи
        }
    )

    # заголовки запрроса
    headers = {
        "Content-Type": "application/json",  # тип содержимого json
        "Accept": "application/json",  # получаем json
        "Authorization": f"Bearer {giga_token}",
    }
    # Выполнение  POST запроса и получение ответа
    try:
        response = requests.request(
            "POST", url, headers=headers, data=payload, verify=False
        )
        return response
    except requests.RequestException as e:
        print(f"error {e}")
        return -1

###передается промпт и два ключа: 1й - информация основная или уточняющая, 2й - какой критерий мы просим найти
def prompt_processing(prompt, key1, key2):
    with open("responce.json", 'r') as f:
        d = json.load(f) #получение словаря промтов
        print(d[key1][key2])
        answer = get_chat(prompt + d[key1][key2]).json()["choices"][0]["message"]["content"]
        print(answer)
        return answer


###получение словаря
def slovarik(data):
    ans = {}
    for i in data.split('\n'):
        ans[i.split(': ')[0]] = i.split(': ')[1]
    return ans



###передается промпт и два ключа: 1й - информация основная или уточняющая, 2й - какой критерий мы просим найти
def prompt_processing(prompt, key1, key2):
    with open("responce.json", 'r', encoding='utf-8') as f:
        d = json.load(f) #получение словаря промтов
        print(d[key1][key2])
        prompt_1 = prompt + d[key1][key2]
        print(prompt_1)
        answer = get_chat(prompt_1).json()["choices"][0]["message"]["content"]
        print(answer)
        return answer


###получение словаря
def slovarik(data):
    ans = {}
    for i in data.split('\n'):
        ans[i.split(': ')[0]] = i.split(': ')[1]
    return ans

def general_recognition(prompt):
    prompt = (
        "«"
        + str(prompt)
        + "»"
        + (
            " \nНайди ключевые слова и раздели их по категориям: "
            "город, где поесть, метро, время, место. "
            "Напиши мне только слова разделенные по категориям в фомате"
            "'категория(с маленькой буквы)':'подходящее ключевое слово'."
            "Если каких-то ключевых слов в категории нет, напиши в ней"
            "'нет иформации'."
        )
    )
    answer = get_chat(prompt)
    print(answer.json())
    data_general = {}
    data_key = "Город, Где поесть, Метро, Время, Место".split(", ")
    for i in answer.json()["choices"][0]["message"]["content"].split("\n"):
        s = i.split(": ")
        value = s[1].split(", ")
        data_general[s[0]] = value
    return data_general


def cafe(cafe, place):
    prompt = (
        f"Привет, помоги мне пожалуйста. Представь себя Экспертом по кафе и ресторанам в Москве, и расскажи какие"
        f" {cafe} в районе {place} есть. Выведи 3 варианта в виде "
        f"'Название Кафе' : 'Небольшое описание буквально в 50 слов'."
    )
    answer = get_chat(prompt)
    return answer.json()["choices"][0]["message"]["content"]


def interesting_places(data):
    places = data["место"]
    print(places)
    prompt = (f"{places} по заданным местам предложи мне по одному интересному месту, которое можно посмотреть в выше перечислленых местах. "
              f"выведи в формате: Место: интересное место. Каждое новое место выводи с новой строки")
    ans = get_chat(prompt).json()["choices"][0]["message"]["content"]
    print(ans)
    print(type(ans))
    """
    data_interest = {}
    for i in ans.split('\n'):
        data_interest[i.split(': ')[0]] = i.split(': ')[1].strip('-')
    return data_interest
    """
    return ans



def place_of_intrerest(data_general):
    places = data_general["место"]
    print(places)
    prompt = (
        f"Представь, что ты гид по Москве. Тебе нужно сказать мне, что конкретно можно интересного посмотреть 1 обьект интереса в районе {places} Выведи в формате -'Место': - 'Объект инетереса', например Кремль : - ГУМ "
    )

    # Получаем ответ
    answer = get_chat(prompt)

    # Выводим полученный ответ для отладки
    print(answer.json()["choices"][0]["message"]["content"])

    text = answer.json()["choices"][0]["message"]["content"]

    data_places_interest = {}
    for i in text.split('\n\n'):
        i = i.split(':\n')
        data_places_interest[i[0].strip(':')] = i[1].strip('-').split(';\n- ')
    print(data_places_interest)
    """
    # Разбиваем текст по строкам и пробелам
    places_data = text.strip().split("\n")

    # Инициализируем словарь для хранения мест и объектов интереса
    data_places_interest = {}

    # Обрабатываем каждую строку
    for place_info in places_data:
        # Разделяем место и список объектов интереса по ':\n'
        place, interests = place_info.split(": ")
        # Разбиваем объекты интереса по запятой и удаляем лишние пробелы
        data_places_interest[place] = [
            interest.strip() for interest in interests.split(",")
        ]

    return data_places_interest
    """
    return data_places_interest

"""
prompt = "Привет, я хочу прогуляться по ценрту Москвы. Хочу зайти в кремль, парк горького, потом перекусить в италианском кафе, и на последок посмотреть закат с крыши небосркеба в москва сити"
general_data = general_recognition(giga_token, prompt)
print(general_data)
place_data = place_of_intrerest(giga_token, general_data)


print(general_data, "\n\n\n", place_data)

"""
"""
### получение кафешек в районе ###
if 'Где поесть' in data_general.keys():
    answer = cafe(data_general['Где поесть'], data_general['Место'], giga_token)
    print(answer)
"""


"""
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
"""


"""
#получение списка доспупных моделей
url = 'https://gigachat.devices.sberbank.ru/api/v1/models'

payload = {}
headers = {
    'Accept': 'application/json',
    'Authorization': f"Bearer {giga_token}"
}

response = requests.request("GET", url, headers=headers, data=payload, verify=False)
print(response.text)
"""


"""
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
"""
