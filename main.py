import requests
import json
import sys
import asyncio
import logging
import time


from aiogram import Bot, Dispatcher, html, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC





#####################################################       Считывание конфигурационного файла      ####################


with open('config.json') as config_file:
    config = json.load(config_file)

TOKEN = config['TELEGRAM_TOKEN']
API_KEY = config['API_KEY']


######################################################      Ботоводство     ############################################





# Инициализация бота и диспетчера с памятью состояний
bot = Bot(token=TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)


# Определение состояний
class PointForm(StatesGroup):
    start_point = State()  # Состояние для ввода начальной точки
    intermediate_points = State()  # Состояние для ввода промежуточных точек
    end_point = State()  # Состояние для ввода конечной точки


@dp.message(Command("get_route"))
async def start(message: Message, state: FSMContext):
    await message.answer("Введите начальную точку:")
    await state.set_state(PointForm.start_point)


# Обработчик ввода начальной точки
@dp.message(PointForm.start_point)
async def enter_start_point(message: Message, state: FSMContext):
    # Сохраняем начальную точку
    await state.update_data(start_point=message.text)

    # Спрашиваем про промежуточные точки
    await message.answer("Введите промежуточные точки (по одной за раз). Когда закончите, напишите 'Стоп'.")
    await state.set_state(PointForm.intermediate_points)


# Обработчик ввода промежуточных точек
@dp.message(PointForm.intermediate_points, F.text.lower() != "стоп")
async def enter_intermediate_points(message: Message, state: FSMContext):
    data = await state.get_data()

    # Добавляем новую промежуточную точку в список
    intermediate_points = data.get("intermediate_points", [])
    intermediate_points.append(message.text)
    await state.update_data(intermediate_points=intermediate_points)

    # Продолжаем диалог
    await message.answer("Введите ещё одну промежуточную точку или напишите 'Стоп' для завершения.")


# Обработчик, когда пользователь вводит "Стоп"
@dp.message(PointForm.intermediate_points, F.text.lower() == "стоп")
async def stop_intermediate_points(message: Message, state: FSMContext):
    # Спрашиваем про конечную точку
    await message.answer("Введите конечную точку:")
    await state.set_state(PointForm.end_point)


# Обработчик ввода конечной точки
@dp.message(PointForm.end_point)
async def enter_end_point(message: Message, state: FSMContext):
    # Сохраняем конечную точку
    await state.update_data(end_point=message.text)

    # Получаем все данные
    data = await state.get_data()
    start_point = data.get("start_point")
    intermediate_points = data.get("intermediate_points", [])
    end_point = data.get("end_point")

    # Формируем и выводим список всех точек
    points = [f"Начальная: {start_point}"] + \
             [f"Промежуточная: {point}" for point in intermediate_points] + \
             [f"Конечная: {end_point}"]

    await message.answer("\n".join(points))

    points = [start_point] + intermediate_points + [end_point]
    link = get_good_route(generate_map_link(points))

    await message.answer(link)
    intermediate_points = None
    # Заканчиваем состояние
    await state.clear()


@dp.message(CommandStart())
async def command_start_handler(message: Message) -> None:
    await message.answer(f"Hello, {html.bold(message.from_user.full_name)}!")



async def main() -> None:
    # Initialize Bot instance with default bot properties which will be passed to all API calls
    bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))

    # And the run events dispatching
    await dp.start_polling(bot)


####################################################        Запросы к барузеру      ####################################


def get_good_route(link):
    try:

        # Настройки для headless режима (запуск без GUI)
        chrome_options = Options()
        #chrome_options.add_argument("--headless")  # Запуск в headless режиме
        #chrome_options.add_argument("--window-size=1920x1080")
        #chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.61 Safari/537.36")
        #chrome_options.add_argument("--disable-gpu")  # отключаем GPU для headless режима


        # Путь к драйверу
        path_to_driver = r"C:\Users\abrac\Desktop\chromedriver-win64\chromedriver.exe"

        # Инициализация службы ChromeDriver
        service = Service(path_to_driver)

        # Инициализация драйвера
        driver = webdriver.Chrome(service=service, options=chrome_options)


        # Открываем страницу
        driver.get(link)
        # Сохраняем первоначальный URL
        initial_url = driver.current_url


        time.sleep(2)
        # Ищем кнопку и кликаем по ней
        # Ожидание появления кнопки
        try:
            button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, '/html/body/div[1]/div[2]/div[11]/div/div[1]/div[1]/div[1]/div/div[1]/div/div/div[1]/form/div[3]/div[2]'))
            )

            # Клик по кнопке
            button.click()

            # Ищем кнопку и кликаем по ней
            # Ожидание появления кнопки

            button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, '/html/body/div[7]/div[2]/div/div[2]/button'))
            )

            # Клик по кнопке
            button.click()
        except Exception as e:
            print(e)
        current_url = driver.current_url

        for i in range(20):
            if initial_url != driver.current_url:
                current_url = driver.current_url
                print(f"Измененная ссылка: {current_url}")
                # Закрываем браузер
                driver.quit()
                break
            else:
                time.sleep(1)
        return current_url
    except Exception as e:
        return e


######################################################      Функции         ############################################


def get_cords(location_name):
    location_cords = None
    try:
        # Запросы к API для получения координат места
        response_location = requests.get(
            f'https://catalog.api.2gis.com/3.0/items/geocode?q={location_name}&fields=items.point&key={API_KEY}')

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
                float(location_item["point"]["lon"])
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
    # Запросы к API
    response_place = requests.get(
        f'https://catalog.api.2gis.com/3.0/items?q={input_text}&location=37.620262,55.761734&radius=1000&key={API_KEY}')

    # Преобразование ответа в JSON
    response_place = response_place.json()

    # Извлечение координат
    try:
        if response_place['result']['items']:  # Проверяем, есть ли элементы в списке
            address_name = response_place['result']['items'][0]['address_name']
        else:
            print("No items found.")

    except Exception as e:
        print(f"Ошибка обработки данных: {e}")
        return e

    return address_name


def generate_map_link(places):
    places_cords = []

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



if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())
