import time
import re
import random
import requests
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup

# --- КОНФІГУРАЦІЯ ---
TEMP_MAIL_URL = "https://i-tv.top/tempmail/index.php"
CHECK_MAIL_URL = "https://i-tv.top/tempmail/check.php"
MY_PANEL_URL = "https://i-tv.top/uspeh/?tab=uspeh"

def get_random_word():
    """Повертає випадкове просте слово для логіна."""
    words = [
        "stol", "voda", "nebo", "park", "kofe", "pult", "site", "link", 
        "mart", "leto", "pivo", "zoom", "work", "boss", "task", "fast",
        "orig", "priz", "skat", "plot", "krok", "stul", "glob", "tema"
    ]
    return random.choice(words)

def get_temp_email_with_custom_login(driver, wait):
    """Заходить на TempMail, міняє логін через інтерфейс і забирає пошту."""
    try:
        new_login = get_random_word()
        driver.get(TEMP_MAIL_URL)
        print(f"[*] Перехід на TempMail. Встановлюємо логін: {new_login}")

        # 1. Натискаємо кнопку "Изменить"
        change_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Изменить')]")))
        change_btn.click()
        
        # 2. Вводимо логін у поле (із затримкою для появи модального вікна)
        input_field = wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "input[type='text']")))
        input_field.clear()
        input_field.send_keys(new_login)
        
        # 3. Натискаємо "СОХРАНИТЬ"
        save_btn = driver.find_element(By.XPATH, "//button[contains(., 'СОХРАНИТЬ')]")
        save_btn.click()
        
        # 4. Пауза для оновлення сесії на сервері
        time.sleep(3)
        
        # 5. Отримуємо фінальну адресу
        email_element = wait.until(EC.presence_of_element_located((By.ID, "emailText")))
        final_email = email_element.text.strip()
        
        print(f"[+] Пошта сконфігурована: {final_email}")
        return final_email
    except Exception as e:
        print(f"[-] Помилка при зміні логіна на сайті: {e}")
        return None

def wait_for_activation_link(session, email):
    """Очікує на лист підтвердження в поштовій скриньці."""
    print(f"[*] Очікуємо на лист для {email}...")
    pattern = r'https://billing\.uspeh\.tv/verify-email\?token=[a-zA-Z0-9]+'
    for _ in range(60): 
        time.sleep(5)
        try:
            response = session.get(f"{CHECK_MAIL_URL}?lang=ru&nocache={time.time()}", timeout=10)
            link_match = re.search(pattern, response.text)
            if link_match:
                return link_match.group(0)
        except:
            continue
    return None

# --- ЗАПУСК БРАУЗЕРА ---
print("[*] Ініціалізація маскованого браузера...")

options = uc.ChromeOptions()
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--disable-gpu")
options.add_argument("--window-size=1920,1080")

try:
    driver = uc.Chrome(
        options=options, 
        headless=True, 
        version_main=145, 
        use_subprocess=False
    ) 
    wait = WebDriverWait(driver, 30)
except Exception as e:
    print(f"[*] Спроба №2: автоматичний підбір драйвера...")
    try:
        driver = uc.Chrome(options=options, headless=True, use_subprocess=False)
        wait = WebDriverWait(driver, 30)
    except Exception as e2:
        print(f"[-] Критична помилка запуску: {e2}")
        exit()

try:
    # 1. Отримання налаштованої пошти через інтерфейс вашого сайту
    email_addr = get_temp_email_with_custom_login(driver, wait)
    if not email_addr: 
        raise Exception("Не вдалося сконфігурувати тимчасову пошту через інтерфейс")
    
    # Створюємо сесію requests і копіюємо куки з Selenium для перевірки пошти
    py_session = requests.Session()
    for cookie in driver.get_cookies():
        py_session.cookies.set(cookie['name'], cookie['value'])

    username = email_addr.split('@')[0]
    password = "VipPassword123!"

    # 2. Реєстрація на Uspeh TV
    driver.get("https://billing.uspeh.tv/register")
    time.sleep(2)
    
    wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "input[type='email']"))).send_keys(email_addr)
    driver.find_element(By.CSS_SELECTOR, "input[type='text']").send_keys(username)
    
    pass_inputs = driver.find_elements(By.CSS_SELECTOR, "input[type='password']")
    pass_inputs[0].send_keys(password)
    pass_inputs[1].send_keys(password)
    
    driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
    print("[*] Форму реєстрації відправлено")

    # 3. Активація через посилання
    activation_link = wait_for_activation_link(py_session, email_addr)
    if not activation_link:
        raise Exception("Лист активації не знайдено")
    
    driver.get(activation_link)
    print("[+] Аккаунт активовано")

    # 4. Авторизація
    wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "input[type='password']")))
    driver.find_element(By.CSS_SELECTOR, "input[type='text'], input[name='login']").send_keys(email_addr)
    driver.find_element(By.CSS_SELECTOR, "input[type='password']").send_keys(password)
    driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
    print("[*] Вхід виконано")

    # 5. Пошук токена
    print("[*] Очікуємо завантаження токена...")
    time.sleep(12) 
    
    final_token = None
    page_source = driver.page_source
    potential_tokens = re.findall(r'[A-Za-z0-9]{16}', page_source)
    
    for t in potential_tokens:
        if t not in ["VipPassword123", "verify-email"]:
            final_token = t
            break

    if final_token:
        print(f"[УСПІХ] ТОКЕН ЗНАЙДЕНО: {final_token}")
        
        # 6. Оновлення на i-tv.top
        print(f"[*] Перехід на i-tv.top для запису...")
        driver.get(MY_PANEL_URL)
        time.sleep(5)

        driver.execute_script("""
            document.querySelectorAll('#reminderOverlay, .modal-backdrop, .toast-container').forEach(el => el.remove());
            document.body.style.overflow = 'auto';
        """)

        input_field = wait.until(EC.presence_of_element_located((By.NAME, "input_data")))
        driver.execute_script("arguments[0].value = arguments[1];", input_field, final_token)
        driver.execute_script("document.querySelector('form').submit();")
        
        print("[+++] ДАНІ ВІДПРАВЛЕНО НА СЕРВЕР")
        time.sleep(5) 
    else:
        print("[-] Помилка: Токен не знайдено.")
        driver.save_screenshot("token_missing_debug.png")

except Exception as e:
    print(f"[-] Сталася помилка: {e}")
    driver.save_screenshot("final_error.png")

finally:
    if 'driver' in locals():
        driver.quit()
