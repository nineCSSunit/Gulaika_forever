import json
import sys
import os
import asyncio
import logging
from random import choice
from datetime import datetime

from aiogram import BaseMiddleware
from aiogram import Bot, Dispatcher, html, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.types import CallbackQuery
from aiogram.filters import StateFilter
from aiogram import Router


from two_gis_API import search_for_cafe_ver_2
from browser import get_good_route
from two_gis_API import generate_map_link
from giga_chat_API import prompt_processing
from giga_chat_API import slovarik
from weather import get_weather_forecast
from recomendations import get_recommendations

#####################################################       Считывание конфигурационного файла      ####################


with open("config.json", "r", encoding="utf-8") as config_file:
    config = json.load(config_file)
with open("phrases.json", "r", encoding="utf-8") as phrases_file:
    phrases = json.load(phrases_file)

TOKEN = config["TELEGRAM_TOKEN"]

####################################################        Логирование         ########################################


class Logger:
    def __init__(self, file_path):
        self.terminal = sys.stdout

        # Проверка на существование файла и создание, если его нет
        if not os.path.exists(file_path):
            with open(file_path, 'w'): pass  # Это создаст пустой файл, если он не существует

        self.log = open(file_path, "a")

    def write(self, message):
        self.terminal.write(message)  # Печать в консоль
        self.log.write(message)  # Запись в файл

    def flush(self):
        self.terminal.flush()
        self.log.flush()


# Перенаправляем stdout
sys.stdout = Logger("log.txt")


######################################################      Ботоводство     ############################################


# Инициализация бота и диспетчера с памятью состояний
bot = Bot(token=TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

router = Router()
dp.include_router(router)


# Определяем состояния (машина состояний)
class PointForm(StatesGroup):
    start_point = State()  # Состояние для ввода начальной точки
    intermediate_points = State()  # Состояние для ввода промежуточных точек
    end_point = State()  # Состояние для ввода конечной точки


class PromptStates(StatesGroup):
    waiting_for_start = State()
    waiting_for_prompt = State()  # Ожидание начального промпта от пользователя
    waiting_for_start_point = State()  # Ожидание начальной точки
    waiting_for_end_point = State()  # Ожидание конечной точки
    waiting_for_time = State()  # Ожидание времени
    waiting_for_metro = State()  # Ожидание ближайшего метро
    waiting_for_area = State()  # Ожидание района
    waiting_for_eat = State()  # Ожидание информации о кафе
    waiting_for_cafe_choice = State()  # Ожидание выбора кафе
    waiting_for_weather = State()   #Рекомендации Интересных мест
    waiting_for_recommendations = State()   #Рекомендации Интересных мест




# Хранилище активных задач пользователей
active_tasks = {}


# Middleware для автоматической отмены задач. Он перехватывает ВСЕ команды, что бы cancel не зачитывался за промпт
class TaskManagerMiddleware(BaseMiddleware):
    async def __call__(self, handler, event: Message, data: dict):
        user_id = event.from_user.id

        # Завершаем активную задачу, если она есть
        if task := active_tasks.get(user_id):
            task.cancel()
            del active_tasks[user_id]

        # Создаём контейнер для новой задачи
        loop = asyncio.get_event_loop()
        task = loop.create_task(handler(event, data))
        active_tasks[user_id] = task

        try:
            return await task
        except asyncio.CancelledError:
            # Если задача была отменена, обработаем это здесь (опционально)
            pass
        finally:
            # Убираем задачу из хранилища после её завершения
            active_tasks.pop(user_id, None)


# Регистрация Middleware
dp.message.middleware(TaskManagerMiddleware())


# Пример обработки команд
@dp.message(Command("start"))
async def start_handler(message: Message, state: FSMContext):
    await state.clear()
    user_name = message.from_user.username
    text = (
        f"Привет, {user_name}! 👋\n\n"
        f"Я бот, который помогает составить идеальную прогулку. Просто расскажи, что ты хочешь: куда пойти, что посмотреть, или какое место ищешь. Чем больше информации ты дашь сразу, тем точнее будет результат. Если чего-то не хватит, я обязательно спрошу!\n\n"
        f"✨ Что я умею?\n"
        f"- Помогу выбрать места для прогулки: парки, музеи, уютные кафе и многое другое.\n"
        f"- Составлю маршрут с учётом твоих предпочтений.\n"
        f"- Расскажу о погоде в районе прогулки.\n"
        f"- Если мне не хватит информации, я уточню детали, чтобы результат был точным.\n\n"
        f"✅ Просто напиши мне, куда хочешь пойти или что ищешь, и мы начнём!"
        "\n\n"
        f"Начнём? 🌿\n"
        f"Выхови get_walk что бы начать составлять прогулку, или нажми на кнопочку "
    )

    def create_start_keyboard():
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Начать прогулку 🌿", callback_data="get_walk")]
        ])
        return keyboard

    keyboard = create_start_keyboard()
    await message.answer(text, reply_markup=keyboard)
    await state.set_state(PromptStates.waiting_for_start)


@router.callback_query(StateFilter(PromptStates.waiting_for_start))
async def handle_walk_start(callback_query: CallbackQuery, state: FSMContext):
    if callback_query.data == "get_walk":
        await callback_query.message.answer(
            "Расскажите, какой прогулкой вы хотите насладиться? Чем больше деталей, тем лучше! ✨🌍\n(Например: где, сколько времени, какие места вам интересны, где бы вы перекусили и т. д.)")
        await state.set_state(PromptStates.waiting_for_prompt)





@dp.message(Command("start"), F.chat.type.in_({"group", "supergroup"}))
async def start_command_in_group(message: Message):
    bot_username = (await bot.get_me()).username
    # Проверяем, упомянут ли бот, если команда вызвана в группе
    if message.text == "/start" or message.text == f"/start@{bot_username}":
        await message.reply("Бот активирован в группе!")





@dp.message(Command("cancel"))         # команда для отмены действий, она завершает все состояния, сбрасывая все данные
async def cancel_handler(message: Message, state: FSMContext):
    # Сбрасываем состояние и отменяем текущую задачу
    await state.clear()
    await message.answer("Все действия отменены. Вызови start, что бы начать с начала!")





# Хендлер на команду /prompt
@dp.message(Command("get_walk"))
async def handle_prompt_command(message: Message, state: FSMContext):
    await message.answer("Расскажите, какой прогулкой вы хотите насладиться? Чем больше деталей, тем лучше! ✨🌍\n(Например: где, сколько времени, какие места вам интересны, где бы вы перекусили и т. д.)")
    await state.set_state(PromptStates.waiting_for_prompt)


# Хендлер для обработки введенного промпта
@dp.message(PromptStates.waiting_for_prompt)
async def handle_prompt_input(message: Message, state: FSMContext):
    prompt_text = message.text  # Получаем введенный пользователем текст
    print(f"\n{prompt_text}\n")

    # Выполняем первичную обработку текста
    d = prompt_processing(prompt_text, "base", "base")
    print(f"\n{d}\n")

    # Обработка и сохранение словаря
    d = slovarik(d)
    await state.update_data(prompt_data=d)


    # Запрашиваем следующую недостающую информацию, если она есть
    await request_next_info(d, message, state)


# Функция запроса следующей необходимой информации
async def request_next_info(data, message: Message, state: FSMContext):
    prompts = {
        "начальная точка": (
            PromptStates.waiting_for_start_point,
            "Пожалуйста, укажите начальную точку.",
        ),
        "конечная точка": (
            PromptStates.waiting_for_end_point,
            "Пожалуйста, укажите конечную точку.",
        ),
        "где поесть": (
            PromptStates.waiting_for_eat,
            "Пожалуйста, укажите, где бы хотели поесть.",
        ),
        "время": (PromptStates.waiting_for_time, "Пожалуйста, укажите время."),
        "метро": (
            PromptStates.waiting_for_metro,
            "Пожалуйста, укажите ближайшее метро.",
        ),
        "район": (PromptStates.waiting_for_area, "Пожалуйста, укажите район."),
    }

    # Обновление словаря prompts случайной фразой
    def update_prompts(phrases):
        for key1 in prompts:
            state, _ = prompts[key1]  # Сохраняем текущее состояние
            random_phrase = choice(phrases[key1])  # Берём случайную фразу из JSON
            prompts[key1] = (state, random_phrase)  # Обновляем значение

    # Загрузка фраз из JSON и обновление prompts
    update_prompts(phrases)

    # Теперь prompts содержит случайные фразы
    print(prompts)

    for key, (next_state, prompt_message) in prompts.items():
        if data.get(key) == "нет информации":
            await message.answer(prompt_message)
            await state.set_state(next_state)
            return

    # Если информация о кафе уже есть, предложим выбор кафе пользователю
    if "где поесть" in data and data["где поесть"] != "нет информации":
        await offer_cafes(message, state)



# Функция обновления информации с обработкой `prompt_processing`
async def handle_info_update(message: Message, state: FSMContext, key: str):
    # Настройка параметров для `prompt_processing` в зависимости от ключа
    processing_params = {
        "начальная точка": ("additional", "start"),
        "конечная точка": ("additional", "end"),
        "где поесть": ("additional", "cafe"),
        "время": ("additional", "time"),
        "метро": ("additional", "metro"),
        "район": ("additional", "area"),
    }

    # Получаем параметры для вызова `prompt_processing`
    mode, detail = processing_params.get(key, ("additional", "default"))

    # Выполняем обработку текста с указанными параметрами
    processed_data = prompt_processing(message.text, mode, detail)

    # Получаем текущие данные из состояния и обновляем их
    user_data = await state.get_data()
    prompt_data = user_data["prompt_data"]
    prompt_data[key] = processed_data

    await state.update_data(prompt_data=prompt_data)


    # Проверяем, нужно ли запросить еще что-то
    await request_next_info(prompt_data, message, state)


# Функция для предложения кафе пользователю
async def offer_cafes(message: Message, state: FSMContext):
    user_data = await state.get_data()
    prompt_data = user_data["prompt_data"]
    cafe_type = prompt_data["где поесть"]  # Получаем тип кафе, выбранный пользователем
    points = [point.strip() for point in prompt_data["место"].split(";") if point.strip()]
    """
    Объяснение:
    split(";") — Разделяет строку по ;.
    point.strip() — Убирает лишние пробелы по краям каждого элемента.
    if point.strip() — Исключает пустые элементы (например, если из-за лишнего ; создается пустая строка).
    """
    print(points)

    # Получаем список кафе вокруг заданной точки
    cafes, cashed_cordinates, polygon_string = search_for_cafe_ver_2(cafe_type, points)
    print(cafes)
    print(cashed_cordinates)
    print(polygon_string)


    await state.update_data(cached_cafes=cafes)
    await state.update_data(cashed_cordinates=cashed_cordinates)
    await state.update_data(cached_polygon=polygon_string)

    # Проверка, если кафе не найдены
    if not cafes:
        await message.answer("Не удалось найти кафе по вашему запросу.")
        await state.set_state(PromptStates.waiting_for_recommendations)
        await send_next_recommendation(message, state)
        return

    # Формируем описание для кафе и создаем клавиатуру
    inline_keyboard = []

    for cafe in cafes:
        # Формируем описание для кафе
        reviews_text = (
            f"Отзывы: {cafe['reviews']['general_review_count']} "
            f"(рейтинг: {cafe['reviews']['general_rating']})"
        )
        cafe_info = (
            f"🏠 {cafe['name']}\n"
            f"📍 Адрес: {cafe['address_name']}\n"
            f"⭐ {reviews_text}\n"
            "Выберите кафе, нажав на соответствующую кнопку ниже."
        )

        # Создаем кнопку для каждого кафе
        cafe_button = InlineKeyboardButton(
            text=f"{cafe['name']} - {cafe['reviews']['general_rating']}⭐",
            callback_data=f"choose_cafe:{cafe['id']}",
        )
        # Добавляем кнопку в строку клавиатуры
        inline_keyboard.append([cafe_button])

        # Отправляем информацию о кафе пользователю
        await message.answer(cafe_info)

    # Создаем объект клавиатуры
    keyboard = InlineKeyboardMarkup(inline_keyboard=inline_keyboard)

    # Отправляем клавиатуру в последнем сообщении
    await message.answer("Выберите кафе:", reply_markup=keyboard)

    # Переводим бота в состояние ожидания выбора кафе
    await state.set_state(PromptStates.waiting_for_cafe_choice)





# Хендлер для обработки выбора кафе
@router.callback_query(
    StateFilter(PromptStates.waiting_for_cafe_choice),
    lambda c: c.data.startswith("choose_cafe")
)
async def handle_cafe_choice(callback_query: CallbackQuery, state: FSMContext):
    cafe_id = callback_query.data.split(":")[1]
    user_data = await state.get_data()
    prompt_data = user_data["prompt_data"]
    print(prompt_data)
    # Находим выбранное кафе по id и добавляем его название в "места"
    cafes = user_data["cached_cafes"]
    print(cafes)
    selected_cafe = next((cafe for cafe in cafes if cafe["id"] == cafe_id), None)
    print(selected_cafe)

    if selected_cafe:
        # Добавляем выбранное кафе в список "места"
        if "место" in prompt_data:
            prompt_data["место"] += f";{selected_cafe['address_name']}"
        else:
            prompt_data["место"] = selected_cafe['address_name']
            print(prompt_data)
        await state.update_data(prompt_data=prompt_data)
        print(prompt_data)

        # Сообщаем пользователю о добавлении кафе
        await callback_query.message.answer(
            f"Вы выбрали кафе: {selected_cafe['name']}. Оно добавлено в маршрут."
        )


        # Проверяем, есть ли еще информация, которую нужно запросить
        if 'конечная точка' in prompt_data and 'начальная точка' in prompt_data:
            await state.set_state(PromptStates.waiting_for_weather)
            await send_weather_chose(callback_query.message, state)
        else:
            await request_next_info(prompt_data, callback_query.message, state)






@dp.message(PromptStates.waiting_for_weather)
async def send_weather_chose(entity, state: FSMContext):
    user_data = await state.get_data()
    coordinates = user_data["cashed_cordinates"]
    date = datetime.now().strftime("%Y-%m-%d")
    def create_weather_keyboard():
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="В помещении", callback_data="weather_yes"),
             InlineKeyboardButton(text="На улице", callback_data="weather_no")]
        ])
        return keyboard

    avg_lat = sum(lat for lat, lon in coordinates) / len(coordinates)
    avg_lon = sum(lon for lat, lon in coordinates) / len(coordinates)
    date = str(datetime.now().strftime("%Y-%m-%d"))
    weather = str(get_weather_forecast(avg_lat, avg_lon, date))

    text = (
        "🌦️ Вот прогноз погоды на ближайшие часы:\n\n"
        f"{weather}\n"
        "Реши, куда ты хочешь отправиться — в помещение или на улицу! 😊"
    )
    keyboard = create_weather_keyboard()
    await entity.answer(text, reply_markup=keyboard, parse_mode="Markdown")



# Хендлер для обработки выбора пользователя на этапе погоды
@router.callback_query(
    StateFilter(PromptStates.waiting_for_weather),
    F.data.in_(["weather_yes", "weather_no"])
)
async def handle_weather_choice(callback_query: CallbackQuery, state: FSMContext):
    if callback_query.data == "weather_yes":
        await state.update_data(weather=False)
        await callback_query.answer("Погода учтена")
        await callback_query.message.answer("Погода учтена")
        await state.set_state(PromptStates.waiting_for_recommendations)
        await send_next_recommendation(callback_query.message, state)



    elif callback_query.data == "weather_no":
        await state.update_data(weather=True)
        await callback_query.answer("Погода учтена")
        await callback_query.message.answer("Погода учтена")
        await state.set_state(PromptStates.waiting_for_recommendations)
        await send_next_recommendation(callback_query.message, state)








"""# Пример данных с рекомендациями
recommendations = [
    {"coords": (55.7558, 37.6176), "address": "Красная площадь, 1",
     "description": "Красная площадь - сердце Москвы и знаковое место России, которое окружают величественные архитектурные сооружения, включая Кремль и Собор Василия Блаженного. Здесь проходят важнейшие мероприятия страны."},
    {"coords": (55.7520, 37.6167), "address": "ГУМ",
     "description": "ГУМ - исторический универмаг, известный своим уникальным архитектурным стилем, роскошными витринами и атмосферой старой Москвы. Здесь можно найти как брендовые магазины, так и уютные кафе."},
    {"coords": (55.7539, 37.6208), "address": "Собор Василия Блаженного",
     "description": "Собор Василия Блаженного - символ Москвы, поражающий своими яркими куполами, уникальной архитектурой и исторической значимостью. Это место обязательно стоит посетить для знакомства с культурой России."},
    {"coords": (55.7506, 37.6096), "address": "Зарядье",
     "description": "Зарядье - современный парк с инновационными ландшафтами, концертным залом и уникальным стеклянным мостом, который нависает над Москвой-рекой, предлагая захватывающий вид."},
    {"coords": (55.7602, 37.6184), "address": "Большой театр",
     "description": "Большой театр - один из самых известных оперных и балетных театров мира, знаменитый своей роскошной сценой, богатой историей и выдающимися спектаклями."}
]"""



"""@dp.message(Command("rec"))
async def aaaa(message, state: FSMContext):
    await state.set_state(PromptStates.waiting_for_recommendations)
    await send_next_recommendation(message, state)"""


# Функция для отправки следующей рекомендации

@dp.message(PromptStates.waiting_for_recommendations)
async def send_next_recommendation(entity, state: FSMContext):
    user_data = await state.get_data()
    current_index = user_data.get("current_index", 0)
    recommendations = user_data.get("recommendations", None)

    if recommendations is None:  # Если рекомендаций нет в контексте
        polygon_string = user_data["cached_polygon"]  # Получаем cached_polygon из контекста
        recommendations = get_recommendations(polygon_string)  # Получаем рекомендации
        await state.update_data(recommendations=recommendations)  # Сохраняем в контексте
    print(user_data)
    print(recommendations)

    def create_recommendation_keyboard():
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Добавить✅", callback_data="add"),
             InlineKeyboardButton(text="Следующая⏭", callback_data="next")],
            [InlineKeyboardButton(text="Закончить выбор🔚", callback_data="finish")]
        ])
        return keyboard

    if current_index < len(recommendations):
        recommendation = recommendations[current_index]
        text = (
            f"📍 **Рекомендация**:\n\n"
            f"✨ **{recommendation['name']}**\n\n"
            f"🏠 Описание: **{recommendation['description']}**\n"
            f"📌 Адрес: {recommendation['address']}\n"
        )

        # Добавляем URL, если он есть
        if recommendation.get("url") and recommendation["url"].strip():
            text += f"🔗 Подробнее: [Ссылка]({recommendation['url']})\n"
        keyboard = create_recommendation_keyboard()
        await entity.answer(text, reply_markup=keyboard, parse_mode="Markdown")
        current_index += 1
        await state.update_data(current_index=current_index)
    else:
        await entity.answer("Либо я еще не знаю интересных мест в районе вашей прогулки, либо вы просмотрели все доступные рекомендации.\n"
                            "Для завершения, нажмите 'Закончить выбор')")

        return





# Хендлер для обработки выбора пользователя на этапе рекомендаций
@router.callback_query(
    StateFilter(PromptStates.waiting_for_recommendations),
    F.data.in_(["add", "next", "finish"])
)
async def handle_recommendation_choice(callback_query: CallbackQuery, state: FSMContext):
    # Считываем значение состояния
    user_data = await state.get_data()
    rec_data = user_data.get("recomendation_cords", "")
    current_index = user_data.get("current_index", 0)
    recommendations = user_data.get("recommendations", None)

    print(user_data)

    if callback_query.data == "add":
        added = recommendations[current_index - 1]['coords']
        rec_data += f";{added}"
        await state.update_data(recomendation_cords=rec_data)
        await callback_query.answer("Добавлено!")
        await callback_query.message.answer("Добавлено!")
        await send_next_recommendation(callback_query.message, state)

    elif callback_query.data == "next":
        await callback_query.answer("Следующая рекомендация!")
        await callback_query.message.answer("Следующая рекомендация!")
        await send_next_recommendation(callback_query.message, state)

    elif callback_query.data == "finish":
        await callback_query.answer("Вы закончили выбор!")
        await callback_query.message.answer("Вы закончили выбор!")
        await finish_process(callback_query.message, state)


# Используем обработчик `handle_info_update` для каждого состояния
@dp.message(PromptStates.waiting_for_start_point)
async def handle_start_point(message: Message, state: FSMContext):
    await handle_info_update(message, state, "начальная точка")


@dp.message(PromptStates.waiting_for_end_point)
async def handle_end_point(message: Message, state: FSMContext):
    await handle_info_update(message, state, "конечная точка")


@dp.message(PromptStates.waiting_for_time)
async def handle_time(message: Message, state: FSMContext):
    await handle_info_update(message, state, "время")


@dp.message(PromptStates.waiting_for_metro)
async def handle_metro(message: Message, state: FSMContext):
    await handle_info_update(message, state, "метро")


@dp.message(PromptStates.waiting_for_area)
async def handle_area(message: Message, state: FSMContext):
    await handle_info_update(message, state, "район")


@dp.message(PromptStates.waiting_for_eat)
async def handle_eat(message: Message, state: FSMContext):
    await handle_info_update(message, state, "где поесть")


# Финальная функция для завершения процесса
async def finish_process(message: Message, state: FSMContext):
    user_data = await state.get_data()
    prompt_data = user_data["prompt_data"]
    rec_data = user_data["recomendation_cords"]
    cashed_cordinates = user_data["cashed_cordinates"]

    await message.answer("Спасибо, я составляю тебе маршрут, подожи немного)")
    print(f"\n{prompt_data}\n")


    start_point = prompt_data["начальная точка"]
    intermediate_points_show = prompt_data.get("место", "").split(";")
    end_point = prompt_data["конечная точка"]

    cashed_cordinates = ";".join(f"({lat}, {lon})" for lat, lon in cashed_cordinates)

    intermediate_points = str(cashed_cordinates + rec_data).split(";")

    points = (
        [f"Начальная: {start_point}"]
        + [f"Промежуточная: {point}" for point in intermediate_points]
        + [f"Конечная: {end_point}"]
    )

    point_show =(
        [f"Начальная: {start_point}"]
        + [f"Промежуточная: {point}" for point in intermediate_points_show]
        + [f"Конечная: {end_point}"]
    )


    await message.answer("Вот ваш маршрут: ")

    await message.answer("\n".join(point_show))
    await message.answer("Сейчас пришлю ссылочку на маршрут!")
    link = get_good_route(
        generate_map_link([start_point] + intermediate_points + [end_point])
    )
    print(link)
    await message.answer(link)

    await state.clear()


@dp.message(Command("route_prompt"))
async def aboba(message: Message, state: FSMContext):
    await message.answer("Вот ваш маршрут: ")
    # Получаем все данные
    data = await state.get_data()
    start_point = data.get("начальная точка")
    intermediate_points = data.get("место", [])
    end_point = data.get("конечная точка")

    # Формируем и выводим список всех точек
    points = (
        [f"Начальная: {start_point}"]
        + [f"Промежуточная: {point}" for point in intermediate_points]
        + [f"Конечная: {end_point}"]
    )

    await message.answer("\n".join(points))

    points = [start_point] + intermediate_points + [end_point]
    link = get_good_route(generate_map_link(points))

    await message.answer(link)


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
    await message.answer(
        "Введите промежуточные точки (по одной за раз). Когда закончите, напишите 'Стоп'."
    )
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
    await message.answer(
        "Введите ещё одну промежуточную точку или напишите 'Стоп' для завершения."
    )


# Обработчик, когда пользователь вводит "Стоп"
@dp.message(PointForm.intermediate_points, F.text.lower() == "стоп")
async def stop_intermediate_points(message: Message, state: FSMContext):
    # Спрашиваем про конечную точку
    await message.answer("Введите конечную точку:")
    await state.set_state(PointForm.end_point)


# Обработчик ввода конечной точки и вывода маршрута
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
    points = (
        [f"Начальная: {start_point}"]
        + [f"Промежуточная: {point}" for point in intermediate_points]
        + [f"Конечная: {end_point}"]
    )

    await message.answer("\n".join(points))

    points = [start_point] + intermediate_points + [end_point]
    link = get_good_route(generate_map_link(points))

    await message.answer(link)
    intermediate_points = None
    # Заканчиваем состояние
    await state.clear()


async def main() -> None:
    # Initialize Bot instance with default bot properties which will be passed to all API calls
    bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))

    # And the run events dispatching
    await dp.start_polling(bot)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())
