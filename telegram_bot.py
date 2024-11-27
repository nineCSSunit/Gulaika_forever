import json
import sys
import asyncio
import logging
from random import choice


from aiogram import Bot, Dispatcher, html, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.types import CallbackQuery
from aiogram.filters import StateFilter


from two_gis_API import search_for_cafe
from browser import get_good_route
from two_gis_API import generate_map_link
from giga_chat_API import general_recognition
from giga_chat_API import place_of_intrerest
from giga_chat_API import prompt_processing
from giga_chat_API import slovarik
from giga_chat_API import interesting_places


#####################################################       Считывание конфигурационного файла      ####################


with open("config.json") as config_file:
    config = json.load(config_file)

TOKEN = config["TELEGRAM_TOKEN"]

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


# Определяем состояния (машина состояний)
class PromptStates(StatesGroup):
    waiting_for_prompt = State()  # Ожидание начального промпта от пользователя
    waiting_for_start_point = State()  # Ожидание начальной точки
    waiting_for_end_point = State()  # Ожидание конечной точки
    waiting_for_time = State()  # Ожидание времени
    waiting_for_metro = State()  # Ожидание ближайшего метро
    waiting_for_area = State()  # Ожидание района
    waiting_for_eat = State()  # Ожидание информации о кафе
    waiting_for_cafe_choice = State()  # Ожидание выбора кафе




@dp.message(Command("start"), F.chat.type.in_({"group", "supergroup"}))
async def start_command_in_group(message: Message):
    bot_username = (await bot.get_me()).username
    # Проверяем, упомянут ли бот, если команда вызвана в группе
    if message.text == "/start" or message.text == f"/start@{bot_username}":
        await message.reply("Бот активирован в группе!")



# Хендлер на команду /prompt
@dp.message(Command('prompt'))
async def handle_prompt_command(message: Message, state: FSMContext):
    await message.answer("Введите свой промпт:")
    await state.set_state(PromptStates.waiting_for_prompt)


# Хендлер для обработки введенного промпта
@dp.message(PromptStates.waiting_for_prompt)
async def handle_prompt_input(message: Message, state: FSMContext):
    prompt_text = message.text  # Получаем введенный пользователем текст
    await message.answer(f"Ваш промпт сохранен: {prompt_text}")

    # Выполняем первичную обработку текста
    d = prompt_processing(prompt_text, "base", "base")
    await message.answer(d)

    # Обработка и сохранение словаря
    d = slovarik(d)
    await state.update_data(prompt_data=d)

    # Запрашиваем следующую недостающую информацию, если она есть
    await request_next_info(d, message, state)


# Функция запроса следующей необходимой информации
async def request_next_info(data, message: Message, state: FSMContext):
    prompts = {
        'начальная точка': (PromptStates.waiting_for_start_point, "Пожалуйста, укажите начальную точку."),
        'конечная точка': (PromptStates.waiting_for_end_point, "Пожалуйста, укажите конечную точку."),
        'где поесть': (PromptStates.waiting_for_eat, "Пожалуйста, укажите, где бы хотели поесть."),
        'время': (PromptStates.waiting_for_time, "Пожалуйста, укажите время."),
        'метро': (PromptStates.waiting_for_metro, "Пожалуйста, укажите ближайшее метро."),
        'район': (PromptStates.waiting_for_area, "Пожалуйста, укажите район.")
    }

    # Загружаем фразы из JSON-файла
    def load_phrases(file_path="phrases.json"):
        with open(file_path, "r", encoding="utf-8") as file:
            return json.load(file)

    # Обновление словаря prompts случайной фразой
    def update_prompts(phrases):
        for key1 in prompts:
            state, _ = prompts[key1]  # Сохраняем текущее состояние
            random_phrase = choice(phrases[key1])  # Берём случайную фразу из JSON
            prompts[key1] = (state, random_phrase)  # Обновляем значение

    # Загрузка фраз из JSON и обновление prompts
    phrases = load_phrases()
    update_prompts(phrases)

    # Теперь prompts содержит случайные фразы
    print(prompts)


    for key, (next_state, prompt_message) in prompts.items():
        if data.get(key) == 'нет информации':
            await message.answer(prompt_message)
            await state.set_state(next_state)
            return

    # Если информация о кафе уже есть, предложим выбор кафе пользователю
    if 'где поесть' in data and data['где поесть'] != 'нет информации':
        await offer_cafes(message, state)
    else:
        await finish_process(message, state)


# Функция обновления информации с обработкой `prompt_processing`
async def handle_info_update(message: Message, state: FSMContext, key: str):
    # Настройка параметров для `prompt_processing` в зависимости от ключа
    processing_params = {
        'начальная точка': ("additional", "start"),
        'конечная точка': ("additional", "end"),
        'где поесть': ("additional", "cafe"),
        'время': ("additional", "time"),
        'метро': ("additional", "metro"),
        'район': ("additional", "area")
    }

    # Получаем параметры для вызова `prompt_processing`
    mode, detail = processing_params.get(key, ("additional", "default"))

    # Выполняем обработку текста с указанными параметрами
    processed_data = prompt_processing(message.text, mode, detail)

    # Получаем текущие данные из состояния и обновляем их
    user_data = await state.get_data()
    prompt_data = user_data['prompt_data']
    prompt_data[key] = processed_data
    await state.update_data(prompt_data=prompt_data)

    # Проверяем, нужно ли запросить еще что-то
    await request_next_info(prompt_data, message, state)


# Функция для предложения кафе пользователю
async def offer_cafes(message: Message, state: FSMContext):
    user_data = await state.get_data()
    prompt_data = user_data['prompt_data']
    cafe_type = prompt_data['где поесть']  # Получаем тип кафе, выбранный пользователем
    points = prompt_data['место'].split(', ')
    print(points)

    # Получаем список кафе вокруг заданной точки
    cafes = search_for_cafe(cafe_type, points)
    await state.update_data(cached_cafes=cafes)

    # Проверка, если кафе не найдены
    if not cafes:
        await message.answer("Не удалось найти кафе по вашему запросу.")
        await finish_process(message, state)
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
            callback_data=f"choose_cafe:{cafe['id']}"
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
@dp.callback_query(StateFilter(PromptStates.waiting_for_cafe_choice), lambda c: c.data.startswith('choose_cafe'))
async def handle_cafe_choice(callback_query: CallbackQuery, state: FSMContext):
    cafe_id = callback_query.data.split(':')[1]
    user_data = await state.get_data()
    prompt_data = user_data['prompt_data']
    print(prompt_data)
    # Находим выбранное кафе по id и добавляем его название в "места"
    cafes = user_data['cached_cafes']
    print(cafes)
    selected_cafe = next((cafe for cafe in cafes if cafe['id'] == cafe_id), None)
    print(selected_cafe)

    if selected_cafe:
        # Добавляем выбранное кафе в список "места"
        if 'место' in prompt_data:
            prompt_data['место'] += f", {selected_cafe['name'].replace(",", "")}"
        else:
            prompt_data['место'] = selected_cafe['name']
            print(prompt_data)
        await state.update_data(prompt_data=prompt_data)

        # Сообщаем пользователю о добавлении кафе
        await callback_query.message.answer(f"Вы выбрали кафе: {selected_cafe['name']}. Оно добавлено в маршрут.")

        # Проверяем, есть ли еще информация, которую нужно запросить
        if 'конечная точка' in prompt_data and 'начальная точка' in prompt_data:
            await finish_process(callback_query.message, state)
        else:
            await request_next_info(prompt_data, callback_query.message, state)


# Используем обработчик `handle_info_update` для каждого состояния
@dp.message(PromptStates.waiting_for_start_point)
async def handle_start_point(message: Message, state: FSMContext):
    await handle_info_update(message, state, 'начальная точка')


@dp.message(PromptStates.waiting_for_end_point)
async def handle_end_point(message: Message, state: FSMContext):
    await handle_info_update(message, state, 'конечная точка')


@dp.message(PromptStates.waiting_for_time)
async def handle_time(message: Message, state: FSMContext):
    await handle_info_update(message, state, 'время')


@dp.message(PromptStates.waiting_for_metro)
async def handle_metro(message: Message, state: FSMContext):
    await handle_info_update(message, state, 'метро')


@dp.message(PromptStates.waiting_for_area)
async def handle_area(message: Message, state: FSMContext):
    await handle_info_update(message, state, 'район')


@dp.message(PromptStates.waiting_for_eat)
async def handle_eat(message: Message, state: FSMContext):
    await handle_info_update(message, state, 'где поесть')


# Финальная функция для завершения процесса
async def finish_process(message: Message, state: FSMContext):
    user_data = await state.get_data()
    prompt_data = user_data['prompt_data']

    await message.answer(f"Спасибо! Вот окончательная информация:\n{prompt_data}")
    await message.answer("Вот ваш маршрут: ")

    start_point = prompt_data['начальная точка']
    intermediate_points = prompt_data.get('место', "").split(', ')
    end_point = prompt_data['конечная точка']

    points = (
            [f"Начальная: {start_point}"]
            + [f"Промежуточная: {point}" for point in intermediate_points]
            + [f"Конечная: {end_point}"]
    )

    await message.answer("\n".join(points))

    link = get_good_route(generate_map_link([start_point] + intermediate_points + [end_point]))
    print(link)
    await message.answer(link)

    await state.clear()


@dp.message(Command("route_prompt"))
async def aboba(message: Message, state: FSMContext):
    await message.answer("Вот ваш маршрут: ")
    # Получаем все данные
    data = await state.get_data()
    start_point = data.get('начальная точка')
    intermediate_points = data.get('место', [])
    end_point = data.get('конечная точка')

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

"""
@dp.message(CommandStart())
async def command_start_handler(message: Message) -> None:
    await message.answer(f"Hello, {html.bold(message.from_user.full_name)}!")
"""

async def main() -> None:
    # Initialize Bot instance with default bot properties which will be passed to all API calls
    bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))

    # And the run events dispatching
    await dp.start_polling(bot)




if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())
