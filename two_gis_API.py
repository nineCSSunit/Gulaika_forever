"""

Этот модуль организует все запросы к API 2Gis, создает сырую ссылку на карты

♪(^∇^*)

"""

from time import perf_counter_ns
from shapely.geometry import Polygon
from shapely.ops import transform
import requests
import json
import re

####################################################       Считывание конфигурационного файла      ####################


with open("config.json") as config_file:
    config = json.load(config_file)

API_KEY = config["API_KEY"]


########################################      Функции 2Gis_API        ##################################################


# Функция получает на вход 1 место / адрес и выдает его координаты
def get_cords(location_name):
    location_cords = None
    location_name = str(
        location_name
    )  # P.S Если хотим реализовать межгород, то придется изменить функцию ==> и код)
    """if "москва" in location_name.lower(): # Добавления ключевого слова москва, что бы API лучше работал и выдавал координаты только в москве
        location_name = (
            location_name.replace("Москва", "").replace("москва", "").strip()
        )

        location_name = "Москва, " + location_name
        print("Полученный Адрес:        ", location_name)

    if not ("москва" in location_name.lower()):
        location_name = "Москва, " + location_name
        print("Полученный Адрес:        ", location_name)"""

    pattern = r"^\(-?\d+\.\d+,\s*-?\d+\.\d+\)$"
    if re.match(pattern, location_name.strip()):
        match = re.match(r"\(([^,]+), ([^)]+)\)", location_name)
        if match:
            location_cords = [float(match.group(1)), float(match.group(2))]
            print("Сэкономлен 1 запрос")
        return location_cords

    location_name = "Москва, " + location_name
    print("Полученный Адрес:        ", location_name)

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


# Создает сырую ссылку на карты
def make_link(places_cords):
    link = f"https://yandex.ru/maps/?rtext="

    for i in places_cords:
        link += (
            f"{i[0]},{i[1]}~"  # для кооректной ссылки требуются перечисление координат
        )

    link = link[:-1]
    link += "&rtt=walking"

    return link


def get_coordinates_string(locations):
    coordinates = []
    for place in locations:
        address = search_for_place(place)  # Получаем адрес точки
        coords = get_cords(address)  # Получаем координаты точки [lat, lon]
        # Добавляем точку в формате (долгота, широта) с округлением до 4 знаков после запятой
        coordinates.append(
            (round(coords[1], 4), round(coords[0], 4))
        )  # (долгота, широта)

    # Находим минимальные и максимальные координаты
    min_lon = min(coord[0] for coord in coordinates)  # минимальная долгота
    max_lon = max(coord[0] for coord in coordinates)  # максимальная долгота
    min_lat = min(coord[1] for coord in coordinates)  # минимальная широта
    max_lat = max(coord[1] for coord in coordinates)  # максимальная широта

    # Формируем точки для прямоугольника
    left_top = f"{min_lon}%2C{max_lat}"  # Верхняя левая точка
    right_bottom = f"{max_lon}%2C{min_lat}"  # Нижняя правая точка

    return [left_top, right_bottom]


# запрос к API для получения адреса места
def search_for_place(input_text):
    address_name = input_text

    # Обработка input_text
    input_text = str(input_text)
    print("input_text       ", input_text)

    pattern = r"^\(-?\d+\.\d+,\s*-?\d+\.\d+\)$"
    if re.match(pattern, input_text.strip()):
        print("Сэкономлен 1 запрос")
        return input_text

    # Запросы к API
    response_place = requests.get(
        f"https://catalog.api.2gis.com/3.0/items?q={input_text}&city_id=4504222397630173&key={API_KEY}"
    )

    # Преобразование ответа в JSON
    response_place = response_place.json()

    # Извлечение координат
    try:
        if response_place["result"]["items"]:  # Проверяем, есть ли элементы в списке
            address_name = response_place["result"]["items"][0]["address_name"]
            print(address_name)
            return address_name
        else:
            print("No items found.")

    except Exception as e:
        print(f"Ошибка обработки данных: {e}")
        return input_text

    return address_name


# Функция, обединяющая все предыдущии в этом модуле, по списку с местами в str выдает сырую ссылку на карты
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


def search_for_cafe(cafe_name, poligon_points_list):
    address_names = None

    # Обработка input_text
    input_text = str(cafe_name)

    polygon_string = get_coordinates_string(poligon_points_list)
    print(polygon_string)

    # Запросы к API
    response_place = requests.get(
        f"https://catalog.api.2gis.com/3.0/items?q={input_text}&fields=items.description,items.reviews&point1={polygon_string[0]}&point2={polygon_string[1]}&page_size=3&key={API_KEY}"
    )

    # Преобразование ответа в JSON
    response_place = response_place.json()
    print(response_place)

    # Извлечение координат
    try:
        if response_place["result"]["items"]:  # Проверяем, есть ли элементы в списке
            address_names = response_place["result"]["items"]
            print(address_names)
        else:
            print("No items found.")

    except Exception as e:
        print(f"Ошибка обработки данных: {e}")
        return e

    return address_names


def get_scaled_polygon_string(locations, scale_factor=1.3):
    coordinates = []
    cached_coordinates = []

    for place in locations:
        address = search_for_place(place)  # Получаем адрес точки
        coords = get_cords(address)  # Получаем координаты точки [lat, lon]
        # Добавляем точку в формате (долгота, широта) с округлением до 6 знаков после запятой
        coordinates.append(
            (round(coords[1], 6), round(coords[0], 6))
        )  # (долгота, широта)
        cached_coordinates.append(
            (round(coords[0], 4), round(coords[1], 4))
        )

    if len(coordinates) < 3:
        raise ValueError("Для построения полигона необходимо минимум 3 точки.")

    # Находим центроид (среднюю точку)
    centroid_lon = sum(coord[0] for coord in coordinates) / len(coordinates)
    centroid_lat = sum(coord[1] for coord in coordinates) / len(coordinates)

    # Масштабируем точки относительно центроида
    scaled_coordinates = []
    for lon, lat in coordinates:
        new_lon = centroid_lon + (lon - centroid_lon) * scale_factor
        new_lat = centroid_lat + (lat - centroid_lat) * scale_factor
        scaled_coordinates.append((round(new_lon, 6), round(new_lat, 6)))

    # Замыкаем полигон, добавляя первую точку в конец
    scaled_coordinates.append(scaled_coordinates[0])

    # Создаем полигон
    polygon = Polygon(scaled_coordinates)

    # Проверяем и исправляем полигон, если он некорректный
    if not polygon.is_valid:
        polygon = polygon.buffer(0)  # Исправляет самопересечения

    # Упрощаем полигон для большей корректности
    simplified_polygon = polygon.simplify(0.00001, preserve_topology=True)

    # Преобразуем обратно в WKT
    valid_coordinates = [(round(coord[0], 6), round(coord[1], 6)) for coord in simplified_polygon.exterior.coords]
    polygon_coords = ",".join(f"{lon} {lat}" for lon, lat in valid_coordinates)
    polygon_wkt = f"POLYGON(({polygon_coords}))"

    return polygon_wkt, cached_coordinates

def search_for_cafe_ver_2(cafe_name, poligon_points_list):
    address_names = None

    # Обработка input_text
    input_text = str(cafe_name)

    polygon_string, cashed_cordinates = get_scaled_polygon_string(poligon_points_list)
    print(polygon_string)

    # Запросы к API
    response_place = requests.get(
        f"https://catalog.api.2gis.com/3.0/items?q={input_text}&fields=items.description,items.reviews&polygon={polygon_string}&page_size=4&key={API_KEY}"
    )

    # Преобразование ответа в JSON
    response_place = response_place.json()
    print(response_place)

    # Извлечение координат
    try:
        if response_place["result"]["items"]:  # Проверяем, есть ли элементы в списке
            address_names = response_place["result"]["items"]
            print(address_names)
        else:
            print("No items found.")

    except Exception as e:
        print(f"Ошибка обработки данных: {e}")
        return e

    return address_names, cashed_cordinates, polygon_string


# search_for_cafe("Суши бар", ["Кремль", "МХТ Имени чехова", "Третяковская галлерея "])


"""
input_text = "Суши бар"
polygon_string, aaa = get_scaled_polygon_string(['третьяковка', 'бауманский сад', 'гэс-2'])
print(polygon_string)
print(aaa)
response_place = requests.get(
        f"https://catalog.api.2gis.com/3.0/items?q={input_text}&fields=items.description,items.reviews&polygon={polygon_string}&page_size=3&key={API_KEY}"
    )

# Преобразование ответа в JSON
response_place = response_place.json()
print(response_place)

"""