from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

####################################################        Запросы к барузеру      ####################################


def get_good_route(link):
    try:

        # Настройки для headless режима (запуск без GUI)
        chrome_options = Options()
        # chrome_options.add_argument("--headless")  # Запуск в headless режиме
        # chrome_options.add_argument("--window-size=1920x1080")
        # chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.61 Safari/537.36")
        # chrome_options.add_argument("--disable-gpu")  # отключаем GPU для headless режима

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
                EC.element_to_be_clickable(
                    (
                        By.XPATH,
                        "/html/body/div[1]/div[2]/div[11]/div/div[1]/div[1]/div[1]/div/div[1]/div/div/div[1]/form/div[3]/div[2]",
                    )
                )
            )

            # Клик по кнопке
            button.click()

            # Ищем кнопку и кликаем по ней
            # Ожидание появления кнопки

            button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable(
                    (By.XPATH, "/html/body/div[7]/div[2]/div/div[2]/button")
                )
            )

            # Клик по кнопке
            button.click()
        except Exception as e:
            print(e)
        current_url = driver.current_url

        for i in range(30):
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