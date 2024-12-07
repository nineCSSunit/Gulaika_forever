import requests
from datetime import datetime, timezone, timedelta
import json



####################################################       Считывание конфигурационного файла      ####################


with open("config.json") as config_file:
    config = json.load(config_file)

WEATHER_API_KEY = config["WEATHER_API_KEY"]



BASE_URL = "https://api.openweathermap.org/data/3.0/onecall"


def get_weather_forecast(lat, lon, date=None):
    def format_weather_data(weather_data):
        result = ""

        # Перебор всех записей прогноза
        for entry in weather_data:
            # Используем timezone-aware объект для преобразования метки времени в UTC
            dt = datetime.fromtimestamp(entry['dt'], timezone.utc)  # Преобразуем временную метку в дату в UTC
            date_str = dt.strftime('%Y-%m-%d %H:%M:%S')  # Форматируем дату и время

            # Основные данные
            temperature = entry['main']['temp']
            feels_like = entry['main']['feels_like']
            pressure = entry['main']['pressure']
            humidity = entry['main']['humidity']
            weather_description = entry['weather'][0]['description']
            wind_speed = entry['wind']['speed']
            clouds = entry['clouds']['all']

            # Формирование строки для вывода
            result += f"Дата и время: {date_str}\n"
            result += f"Температура: {temperature}°C (ощущается как {feels_like}°C)\n"
            result += f"Погода: {weather_description}\n"
            result += f"Давление: {pressure} гПа\n"
            result += f"Влажность: {humidity}%\n"
            result += f"Скорость ветра: {wind_speed} м/с\n"
            result += f"Облачность: {clouds}%\n"
            result += "-" * 40 + "\n"

        return result

    url = f"http://api.openweathermap.org/data/2.5/forecast"
    params = {
        "lat": lat,
        "lon": lon,
        "appid": WEATHER_API_KEY,
        "units": "metric",
        "cnt": 5,# Прогноз на 5 дней
        "lang": "ru"
    }

    response = requests.get(url, params=params)
    if response.status_code != 200:
        return f"Ошибка при запросе API: {response.status_code}"

    try:
        data = response.json()
        forecasts = data.get("list", [])

        if not forecasts:
            return "Прогноз отсутствует."

        # Если дата не указана, берем прогноз на сегодня и завтра
        if not date:
            today = datetime.now().strftime('%Y-%m-%d')
            tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
            return format_weather_data([f for f in forecasts if today in f["dt_txt"] or tomorrow in f["dt_txt"]])

        # Ищем прогноз на указанную дату
        forecast = [f for f in forecasts if date in f["dt_txt"]]
        if not forecast:
            return f"Прогноз на {date} отсутствует."

        return format_weather_data(forecast)

    except Exception as e:
        return f"Ошибка обработки данных: {e}"



"""
# Пример вызова
lat = 55.7558  # Москва
lon = 37.6176
date = "2024-12-02"  # Прогноз на 2 декабря
print(get_weather_forecast(lat, lon, date))
print(get_weather_forecast(lat, lon))

"""