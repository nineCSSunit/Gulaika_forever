import requests
import json
import sys
import asyncio
import logging
import black
from aiogram import Bot, Dispatcher, html
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.types import Message
from aiogram.filters import Command
from aiogram import F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

with open('config.json') as config_file:
    config = json.load(config_file)

TOKEN = config['TELEGRAM_TOKEN']
API_KEY = config['API_KEY']
######################################################      Ботоводство     ############################################


bot = Bot(token=TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)


# Определяем машину состояний
class RouteForm(StatesGroup):
    start_point = State()  # Ожидание начальной точки
    stop_1 = State()       # Ожидание 1-й промежуточной точки
    stop_2 = State()       # Ожидание 2-й промежуточной точки
    stop_3 = State()       # Ожидание 3-й промежуточной точки
    stop_4 = State()       # Ожидание 4-й промежуточной точки
    stop_5 = State()       # Ожидание 5-й промежуточной точки
    end_point = State()    # Ожидание конечной точки


# Хендлер для команды /get_route
@dp.message(Command("get_route"))
async def start_route(message: Message, state: FSMContext):
    await message.answer("Введите начальную точку:")
    # Устанавливаем состояние ожидания начальной точки
    await state.set_state(RouteForm.start_point)


# Хендлер для получения начальной точки
@dp.message(RouteForm.start_point)
async def process_start_point(message: Message, state: FSMContext):
    # Сохраняем начальную точку
    await state.update_data(start_point=message.text)
    await message.answer("Введите первую промежуточную точку:")
    # Переходим к следующему состоянию - ожидание 1-й промежуточной точки
    await state.set_state(RouteForm.stop_1)


# Хендлер для получения 1-й промежуточной точки
@dp.message(RouteForm.stop_1)
async def process_stop_1(message: Message, state: FSMContext):
    await state.update_data(stop_1=message.text)
    await message.answer("Введите вторую промежуточную точку:")
    await state.set_state(RouteForm.stop_2)


# Хендлер для получения 2-й промежуточной точки
@dp.message(RouteForm.stop_2)
async def process_stop_2(message: Message, state: FSMContext):
    await state.update_data(stop_2=message.text)
    await message.answer("Введите третью промежуточную точку:")
    await state.set_state(RouteForm.stop_3)

# Хендлер для получения 3-й промежуточной точки
@dp.message(RouteForm.stop_3)
async def process_stop_3(message: Message, state: FSMContext):
    await state.update_data(stop_3=message.text)
    await message.answer("Введите четвертую промежуточную точку:")
    await state.set_state(RouteForm.stop_4)

# Хендлер для получения 4-й промежуточной точки
@dp.message(RouteForm.stop_4)
async def process_stop_4(message: Message, state: FSMContext):
    await state.update_data(stop_4=message.text)
    await message.answer("Введите пятую промежуточную точку:")
    await state.set_state(RouteForm.stop_5)

# Хендлер для получения 5-й промежуточной точки
@dp.message(RouteForm.stop_5)
async def process_stop_5(message: Message, state: FSMContext):
    await state.update_data(stop_5=message.text)
    await message.answer("Введите конечную точку:")
    await state.set_state(RouteForm.end_point)



# Хендлер для получения конечной точки и завершения
@dp.message(RouteForm.end_point)
async def process_end_point(message: Message, state: FSMContext):
    # Сохраняем конечную точку
    await state.update_data(end_point=message.text)

    # Получаем все данные маршрута
    data = await state.get_data()

    input_places = [data['start_point'], data['stop_1'], data['stop_2'], data['stop_3'], data['stop_4'], data['stop_5'],
                    data['end_point']]

    for i in range(len(input_places)):
        input_places[i] = get_cords(input_places[i])


    # Отправляем маршрут пользователю
    await message.answer(make_link(total_route(input_places)))

    # Завершаем состояние
    await state.clear()


@dp.message(CommandStart())
async def command_start_handler(message: Message) -> None:
    await message.answer(f"Hello, {html.bold(message.from_user.full_name)}!")



async def main() -> None:
    # Initialize Bot instance with default bot properties which will be passed to all API calls
    bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))

    # And the run events dispatching
    await dp.start_polling(bot)

######################################################      Функции         ############################################


def get_cords(location_name):
    # Запросы к API
    response_location = requests.get(
        f'https://catalog.api.2gis.com/3.0/items/geocode?q={location_name}&fields=items.point&key={API_KEY}')

    # Преобразование ответа в JSON
    response_location = response_location.json()

    # Извлечение координат
    try:
        # Проверка наличия элементов в ответе
        location_item = response_location.get("result", {}).get("items", [])[0]

        # Проверка наличия точки в элементах
        if location_item and "point" in location_item:
            location_cords = [
                float(location_item["point"]["lat"]),
                float(location_item["point"]["lon"])
            ]
        else:
            raise ValueError("Не удалось найти координаты")

        print(f"Координаты {location_name}: {location_cords}")


    except (IndexError, KeyError, ValueError) as e:
        print(f"Ошибка обработки данных: {e}")

    return location_cords


def make_link(places_cords):
    link = f"https://yandex.ru/maps/?rtext="

    for i in places_cords:
        link += f"{i[0]},{i[1]}~"

    link = link[:-1]
    link += "&rtt=auto"

    return link


def poisk(graph):
    route = [0] * (len(graph) - 1)
    route = [1] + route
    c = 0
    for i in range(len(graph) - 1):
        before = route[c]
        c += 1
        s = list(filter(lambda x: x[1] not in route, graph[before]))
        mi = s[0][0]
        for e in s:
            if e[0] <= mi and e[1] not in route:
                if c == len(graph) - 1 and e[1] == len(graph):
                    mi = e[0]
                    route[c] = e[1]
                if e[1] != len(graph):
                    mi = e[0]
                    route[c] = e[1]
    return route


def get_distance_between_two(first_point, second_point):
    url = f"https://routing.api.2gis.com/get_dist_matrix?key={API_KEY}&version=2.0"

    data_send = {
        "points": [
            {
                "lat": first_point[0],
                "lon": first_point[1]
            },
            {
                "lat": second_point[0],
                "lon": second_point[1]
            }
        ],
        "sources": [0],
        "targets": [1],
        "mode": "walking"
    }

    # Выполнение POST-запроса
    response_distance_matrix = requests.post(url, headers={"Content-Type": "application/json"},
                                             data=json.dumps(data_send))

    # Преобразование ответа в JSON
    response_distance_matrix = response_distance_matrix.json()

    '''
    # заготовка если больше 1
    duration = [route["duration"] for route in response_distance_matrix["routes"]]
    duration = duration[0]
    '''

    duration = response_distance_matrix["routes"][0]["duration"]

    # Тест
    # print(get_distance_between_two([55.751401, 37.619025], [55.722549, 37.553834]))

    return duration


def get_key(value, sl, possible):
    for k in sl.keys():
        if sl[k] == value and k not in possible:
            return k


"""

def get_points_in_order(points, max_time, type_0="jam"):
    def get_distance_between_two(first_point, second_point):

        url = f"https://routing.api.2gis.com/get_dist_matrix?key={API_KEY}&version=2.0"

        data_send = {
            "points": [
                {
                    "lat": first_point[0],
                    "lon": first_point[1]
                },
                {
                    "lat": second_point[0],
                    "lon": second_point[1]
                }
            ],
            "sources": [0],
            "targets": [1]
        }

        # Выполнение POST-запроса
        response_distance_matrix = requests.post(url, headers={"Content-Type": "application/json"},
                                                 data=json.dumps(data_send))

        # Преобразование ответа в JSON
        response_distance_matrix = response_distance_matrix.json()

        # заготовка если больше 1
        duration = [route["duration"] for route in response_distance_matrix["routes"]]
        duration = duration[0]

        # Тест
        # print(get_distance_between_two([55.751401, 37.619025], [55.722549, 37.553834]))

        return duration

    # Функция для кэширования расстояний
    def cache_distances(points):
        distance_cache = {}
        for i, point1 in enumerate(points):
            for j, point2 in enumerate(points):
                if i != j and (i, j) not in distance_cache:
                    distance_cache[(i, j)] = get_distance_between_two(point1, point2)
                    distance_cache[(j, i)] = distance_cache[(i, j)]  # Время в обе стороны одинаково
        return distance_cache

    # Функция для вычисления времени на маршрут
    def calculate_route_time(route, distance_cache):
        total_time = 0
        for i in range(len(route) - 1):
            total_time += distance_cache[(route[i], route[i + 1])]
        return total_time

    # Функция для поиска оптимальной перестановки точек
    def find_optimal_permutation(points, distance_cache, max_time):
        n = len(points)
        optimal_route = list(range(n))  # Начальная последовательность точек (в том порядке, как даны)
        best_time = float('inf')  # Инициализируем лучшее время как бесконечность

        # Пробуем все перестановки для промежуточных точек
        for perm in itertools.permutations(range(1, n - 1)):  # Генерация всех перестановок промежуточных точек
            current_route = [0] + list(perm) + [n - 1]  # Формируем маршрут с данной перестановкой
            current_time = calculate_route_time(current_route, distance_cache)

            if current_time <= max_time and current_time < best_time:
                optimal_route = current_route
                best_time = current_time

        return optimal_route, best_time

    # Основная функция для поиска оптимального маршрута с удалением точек при необходимости
    def find_optimal_route(points, max_time):
        n = len(points)

        # Кэшируем расстояния между всеми точками
        distance_cache = cache_distances(points)

        # Ищем оптимальную перестановку промежуточных точек
        optimal_route, best_time = find_optimal_permutation(points, distance_cache, max_time)

        # Если оптимальный маршрут вписывается в заданное время, возвращаем его
        if best_time <= max_time:
            return [points[i] for i in optimal_route], []

        # Иначе начинаем убирать промежуточные точки
        removed_points = []

        # Попробуем разные комбинации промежуточных точек
        for r in range(n - 2, 0, -1):  # Убираем по одной точке, начиная с максимума
            for comb in itertools.combinations(range(1, n - 1), r):  # Пробуем все комбинации промежуточных точек
                comb_route = [0] + list(comb) + [n - 1]
                comb_time = calculate_route_time(comb_route, distance_cache)

                if comb_time <= max_time:
                    # Нашли маршрут, который укладывается в ограничение
                    optimal_route = comb_route
                    removed_points = [points[i] for i in set(range(n)) - set(optimal_route)]
                    return [points[i] for i in optimal_route], removed_points

        # Если ни один маршрут не вписался, возвращаем начальный маршрут и пустой список удаленных точек
        return [points[i] for i in range(n)], []

    optimal_route, removed_points = find_optimal_route(points, max_time)
    return optimal_route


# points = [[55.906905, 37.552504], [55.751401, 37.619025], [55.722549, 37.553834], [55.906905, 37.552504]]
# print(get_points_in_order(points, 10000))
"""

############################################################        Ввод        ########################################
"""
input_places = []
print("Вводите сначала начальную точку, потом конечную,  потом промежуточные, как закончите, нажмите Cntr + D ")

start_location = input("Введите точку старта маршрута: ")

end_location = input("Введите точку конца маршрута: ")


s = input()
while s != '':
    input_places.append(s)
    s = input()


for line in sys.stdin:
    input_places.append(line.strip("\n"))

input_places = [start_location] + input_places + [end_location]

for i in range(len(input_places)):
    input_places[i] = get_cords(input_places[i])
"""
#############################################################       заполнение графов       ############################



def total_route(input_places):

    names = {}
    for i in range(1, len(input_places) + 1):
        names[i] = input_places[i - 1]

    graph = {}
    c = names
    possible = list(names.keys())
    for i in names.keys():
        if i == 1 or i == len(names):
            p = []
            possible = []
            for e in input_places[1: -1]:
                p.append((get_distance_between_two(names[i], e), get_key(e, names, possible)))
            graph[i] = p
        else:
            possible = []
            p = []
            for e in input_places:
                if e != names[i]:
                    p.append((get_distance_between_two(names[i], e), get_key(e, names, possible)))
                    possible.append(p[-1][1])
            graph[i] = p


    start = 1
    end = len(input_places)
    visited = poisk(graph)

    total_route = []
    for i in visited:
        total_route.append(names[i])

    return total_route


# Москва, Псковская, 11
#Москва, Рязанский проспект, 10
#Долгопрудный, Лётная, 8


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())