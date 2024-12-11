import psycopg2
import json
from shapely.wkt import loads
from shapely.geometry import Point
from shapely.geometry import Polygon

#####################################################       Считывание конфигурационного файла      ####################


with open("config.json", "r", encoding="utf-8") as config_file:
    config = json.load(config_file)

PASS = config["POSTGRESS_PASS"]



def get_scaled_polygon_string(locations, scale_factor=1.3):
    coordinates = locations
    '''for place in locations:
        address = search_for_place(place)  # Получаем адрес точки
        coords = get_cords(address)  # Получаем координаты точки [lat, lon]
        # Добавляем точку в формате (долгота, широта) с округлением до 6 знаков после запятой
        coordinates.append(
            (round(coords[1], 6), round(coords[0], 6))
        )  # (долгота, широта)'''

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

    # Форматируем координаты в строку WKT
    polygon_coords = ",".join(f"{lon} {lat}" for lon, lat in scaled_coordinates)
    polygon_wkt = f"POLYGON(({polygon_coords}))"

    return polygon_wkt


# какие районы затрагивает полигон
def which_areas(polygon,  connection):
    with connection.cursor() as cursor:
        pol = loads(polygon)
        cursor.execute("SELECT * FROM areas;")
        rows = cursor.fetchall()
        ans = []
        for row in rows:
            p = Point(float(row[0].split(', ')[0]), float(row[0].split(', ')[1]))
            if pol.contains(p):
                ans.append(row[1])
    return ans




#получение координат интересных мест
def get_cords_of_interesting_places(polygon, areas,  connection):
    with connection.cursor() as cursor:
        ans = []
        pol = loads(polygon)
        for name in areas:
            cursor.execute(f"SELECT * FROM places WHERE area = '{name}';")
            rows = cursor.fetchall()
            for row in rows:
                if len(ans) > 5:
                    break
                p = Point(float(row[1].split(', ')[1]), float(row[1].split(', ')[0]))
                if pol.contains(p):
                    # Добавляем все столбцы в ans
                    ans.append({
                        'adress': row[0],
                        'cords': row[1],
                        'area': row[2],
                        'outdoor': row[3],
                        'url': row[4],
                        'description': row[5],
                        'name': row[6]
                    })
            if len(ans) > 5:
                break

        ans1 = []
        for i in ans:
            ans1.append({
                "name": i['name'],
                "coords": tuple(map(float, i['cords'].split(', '))),  # Преобразуем строку координат в кортеж из float
                "address": i['adress'],
                "description": i['description'],
                "area": i['area'],
                "outdoor": i['outdoor'],
                "url": i['url']
            })
    return ans1





def get_cords_of_interesting(polygon, connection):
    with connection.cursor() as cursor:
        ans = []
        pol = loads(polygon)
        cursor.execute("SELECT * FROM places;")
        rows = cursor.fetchall()

        for row in rows:
            if len(ans) > 5:
                break
            # Проверка координат
            p = Point(float(row[1].split(', ')[1]), float(row[1].split(', ')[0]))
            if pol.contains(p):
                # Добавляем все столбцы в ans
                ans.append({
                    'adress': row[0],
                    'cords': row[1],
                    'area': row[2],
                    'outdoor': row[3],
                    'url': row[4],
                    'description': row[5],
                    'name': row[6]
                })

        ans1 = []
        for i in ans:
            ans1.append({
                "name": i['name'],
                "coords": tuple(map(float, i['cords'].split(', '))),  # Преобразуем строку координат в кортеж из float
                "address": i['adress'],
                "description": i['description'],
                "area": i['area'],
                "outdoor": i['outdoor'],
                "url": i['url']
            })
        return ans1








# Основная функция для получения рекомендаций
def get_recommendations(polygon):
    try:
        config = {
            'host': 'localhost',
            'database': 'db_places',
            'user': 'postgres',
            'password': PASS,
        }
        connection = psycopg2.connect(**config)
        print("[INFO] Successfully connected to the database")
        places = get_cords_of_interesting(polygon, connection)
        print(places)
        return places

    except Exception as e:
        print(f"[ERROR] {e}")
        return None

    finally:
        # Закрываем подключение
        if 'connection' in locals() and connection:
            connection.close()
            print("[INFO] Connection closed")


# Тест
"""
a = get_scaled_polygon_string(locations=[
        [37.661778, 55.765655],
        [37.628891, 55.741328],
        [37.65865, 55.72971]
    ])
print(a)
print(get_recommendations(a))
"""

"""
import matplotlib.pyplot as plt

# Два полигона в формате WKT
polygon1_coords = [(37.66538, 55.771682), (37.622626, 55.740057), (37.661313, 55.724954), (37.66538, 55.771682)]
polygon2_coords = [
    [37.624318, 55.73613],  # 1-я точка
    [37.674823, 55.776965],  # 2-я точка
    [37.611426, 55.75533],   # 3-я точка
    [37.624318, 55.73613]    # Закрытие полигона
]

# Создаем объекты Polygon
polygon1 = Polygon(polygon1_coords)
polygon2 = Polygon(polygon2_coords)

# 1. Площадь полигона
area1 = polygon1.area
area2 = polygon2.area
print(f"Площадь первого полигона: {area1}")
print(f"Площадь второго полигона: {area2}")

# 2. Пересечение (если есть) или расстояние между полигонами
intersection = polygon1.intersection(polygon2)
if intersection.is_empty:
    print("Полигоны не пересекаются.")
else:
    print(f"Пересечение полигона: {intersection}")

# 3. Расстояние между полигонами
distance = polygon1.distance(polygon2)
print(f"Расстояние между полигонами: {distance}")
# Два полигона в формате WKT

# Создаем объекты Polygon
polygon1 = Polygon(polygon1_coords)
polygon2 = Polygon(polygon2_coords)

# Функция для отрисовки полигона
def plot_polygon(polygon, ax, color, label):
    x, y = polygon.exterior.xy  # Получаем координаты для рисования
    ax.fill(x, y, alpha=0.5, fc=color, label=label)  # Заполнение полигона
    ax.plot(x, y, color=color)  # Обводка полигона

# Создаем фигуру для отображения
fig, ax = plt.subplots()

# Рисуем оба полигона
plot_polygon(polygon1, ax, 'blue', 'Полигон 1')
plot_polygon(polygon2, ax, 'red', 'Полигон 2')

# Настройки графика
ax.set_title("Сравнение полигонов")
ax.set_xlabel("Долгота")
ax.set_ylabel("Широта")
ax.legend()

# Показываем график
plt.show()
"""



"""
import geopandas as gpd
import osmnx as ox

# Загружаем геометрические данные
districts = ox.features_from_place("Moscow, Russia", tags={"place": "suburb"})

# Фильтруем только полигоны
polygons = districts[districts.geometry.type.isin(['Polygon', 'MultiPolygon'])]

# Конвертируем GeoDataFrame в формат GeoJSON (удобный для записи в JSON)
polygons_json = polygons.to_json()

# Записываем в файл

    
"""