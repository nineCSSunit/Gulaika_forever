import json
import sys
import asyncio
import logging



from aiogram import Bot, Dispatcher, html, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage


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
    waiting_for_prompt = State()


# Хендлер на команду /prompt
@dp.message(Command('prompt'))
async def handle_prompt_command(message: Message, state: FSMContext):
    await message.answer("Введите свой промпт:")
    # Устанавливаем состояние ожидания промпта
    await state.set_state(PromptStates.waiting_for_prompt)

# Хендлер для обработки введенного промпта
@dp.message(PromptStates.waiting_for_prompt)
async def handle_prompt_input(message: Message, state: FSMContext):
    # Получаем введенный промпт
    prompt_text = message.text

    # Отправляем подтверждение пользователю
    await message.answer(f"Ваш промпт сохранен: {prompt_text}")

    d = prompt_processing(prompt_text, "base", "base")
    await message.answer(d)
    ##отбработка словаря
    d = slovarik(d)
    ###сделано в черновом варианте будет дорабатываться
    if d['где поесть'] != "нет информации":
        await message.answer(f"Могу предложить следующие кафе: {prompt_processing(prompt_text, 'base', 'cafe')}")
    await message.answer(interesting_places(d))

    # Сбрасываем состояние
    await state.clear()
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


@dp.message(CommandStart())
async def command_start_handler(message: Message) -> None:
    await message.answer(f"Hello, {html.bold(message.from_user.full_name)}!")


async def main() -> None:
    # Initialize Bot instance with default bot properties which will be passed to all API calls
    bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))

    # And the run events dispatching
    await dp.start_polling(bot)


"""prompt = "Привет, я хочу прогуляться по ценрту Москвы. Хочу зайти в кремль, парк горького, потом перекусить в италианском кафе, и на последок посмотреть закат с крыши небосркеба в москва сити"
general_data = general_recognition(prompt)
print(general_data)
place_data = place_of_intrerest(general_data)


print(general_data, "\n\n\n", place_data)"""


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())
