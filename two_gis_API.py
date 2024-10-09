import requests
import json


####################################################       Считывание конфигурационного файла      ####################


with open("config.json") as config_file:
    config = json.load(config_file)

API_KEY = config["API_KEY"]


########################################      Функции 2Gis_API        ##################################################


def get_cords(location_name):
    location_cords = None
    location_name = str(location_name)
    if "москва" in location_name.lower():
        location_name = (
            location_name.replace("Москва", "").replace("москва", "").strip()
        )
        location_name = "Москва, " + location_name
        print("location_name     ", location_name)
    if not ("москва" in location_name.lower()):
        location_name = "Москва, " + location_name
        print("location_name     ", location_name)

    try:
        # Запросы к API для получения координат места
        response_location = requests.get(
            f"https://catalog.api.2gis.com/3.0/items/geocode?q={location_name}&fields=items.point&key={API_KEY}"
        )

        # Преобразование ответа в JSON
        response_location = response_location.json()

        # Проверка на наличие результатов
        items = response_location.get("result", {}).get("items", [])
        if not items:  # Если список пустой, выводим сообщение и возвращаем None
            print(f"Координаты для {location_name} не найдены.")
            return None

        # Извлечение координат
        location_item = items[0]
        if location_item and "point" in location_item:
            location_cords = [
                float(location_item["point"]["lat"]),
                float(location_item["point"]["lon"]),
            ]
        else:
            raise ValueError(f"Не удалось найти координаты для {location_name}")

        return location_cords

    except (IndexError, KeyError, ValueError) as e:
        print(f"Ошибка получения координат для {location_name}: {e}")
        return None


def make_link(places_cords):
    link = f"https://yandex.ru/maps/?rtext="

    for i in places_cords:
        link += f"{i[0]},{i[1]}~"

    link = link[:-1]
    link += "&rtt=walking"

    return link


def search_for_place(input_text):
    # Обработка input_text
    input_text = str(input_text)
    if "москва" in input_text.lower():
        input_text = input_text.replace("Москва", "").replace("москва", "").strip()
        input_text = "Москва, " + input_text
        print("input_text     ", input_text)
    if not ("москва" in input_text.lower()):
        input_text = "Москва, " + input_text
        print("input_text", input_text)

    # Запросы к API
    response_place = requests.get(
        f"https://catalog.api.2gis.com/3.0/items?q={input_text}&key={API_KEY}"
    )

    # Преобразование ответа в JSON
    response_place = response_place.json()

    # Извлечение координат
    try:
        if response_place["result"]["items"]:  # Проверяем, есть ли элементы в списке
            address_name = response_place["result"]["items"][0]["address_name"]
            print(address_name)
        else:
            print("No items found.")

    except Exception as e:
        print(f"Ошибка обработки данных: {e}")
        return e

    return address_name


def generate_map_link(places):
    places_adress = []
    places_cords = []
    for adress in places:
        adress = search_for_place(adress)
        if adress:
            places_adress.append(adress)
    # Получаем координаты для каждого места
    for place in places:
        cords = get_cords(place)
        if cords:  # Если координаты найдены, добавляем их в список
            places_cords.append(cords)

    if places_cords:  # Если есть координаты, создаем ссылку
        return make_link(places_cords)
    else:
        print("Не удалось получить координаты для всех мест.")
        return None
