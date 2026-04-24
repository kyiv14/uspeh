import time
import re
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

def get_temp_email():
    """Отримує нову адресу електронної пошти через ваш API."""
    session = requests.Session()
    try:
        response = session.get(TEMP_MAIL_URL, timeout=15)
        soup = BeautifulSoup(response.text, 'html.parser')
        email_element = soup.find(id="emailText")
        if email_element:
            return email_element.text.strip(), session
        return None, None
    except Exception as e:
        print(f"[-] Помилка отримання пошти: {e}")
        return None, None

def wait_for_activation_link(session, email):
    """Очікує на лист підтвердження в поштовій скриньці."""
    print(f"[*] Очікуємо на лист для {email}...")
    # Регулярний вираз для пошуку посилання активації
    pattern = r'https://billing\.uspeh\.tv/verify-email\?token=[a-zA-Z0-9]+'
    for _ in range(60): 
        time.sleep(5)
        try:
            # nocache додано для уникнення старих результатів
            response = session.get(f"{CHECK_MAIL_URL}?lang=ru&nocache={time.time()}", timeout=10)
            link_match = re.search(pattern, response.text)
            if link_match:
                return link_match.group(0)
        except:
            continue
    return None

def get_clean_options():
    """Створює новий об'єкт опцій для кожної спроби запуску (виправляє помилку reuse)."""
    options = uc.ChromeOptions()
    options.add_argument("--headless")  # Обов'язково для GitHub Actions
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    # Маскування автоматизації
    options.add_argument("--disable-blink-features=AutomationControlled")
    return options

# --- ЗАПУСК БРАУЗЕРА ---
print("[*] Ініціалізація маскованого браузера...")

driver = None
try:
    # Спроба №1: Автоматичний підбір драйвера (найбільш стабільний варіант)
    driver = uc.Chrome(options=get_clean_options(), use_subprocess=True) 
    wait = WebDriverWait(driver, 40)
except Exception as e:
    print(f"[*] Спроба №1 не вдалася: {e}. Пробуємо альтернативну конфігурацію...")
    try:
        # Спроба №2: З вимкненим сабпроцесом, якщо перша не пройшла
        driver = uc.Chrome(options=get_clean_options(), use_subprocess=False)
        wait = WebDriverWait(driver, 40)
    except Exception as e2:
        print(f"[-] Критична помилка запуску: {e2}")
        exit(1)

try:
    # 1. Отримання пошти
    email_addr, py_session = get_temp_email()
    if not email_addr: 
        raise Exception("Не вдалося отримати тимчасову пошту")
    
    print(f"[+] Використовуємо пошту: {email_addr}")
    username = email_addr.split('@')[0]
    password = "VipPassword123!"

    # 2. Реєстрація
    driver.get("https://billing.uspeh.tv/register")
    time.sleep(5)
    
    wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "input[type='email']"))).send_keys(email_addr)
    driver.find_element(By.CSS_SELECTOR, "input[type='text']").send_keys(username)
    
    pass_inputs = driver.find_elements(By.CSS_SELECTOR, "input[type='password']")
    pass_inputs[0].send_keys(password)
    pass_inputs[1].send_keys(password)
    
    driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
    print("[*] Форму реєстрації відправлено. Чекаємо на лист...")

    # 3. Активація через посилання
    activation_link = wait_for_activation_link(py_session, email_addr)
    if not activation_link:
        raise Exception("Лист активації не прийшов протягом 5 хвилин")
    
    driver.get(activation_link)
    print("[+] Аккаунт активовано посиланням")
    time.sleep(3)

    # 4. Авторизація
    wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "input[type='password']")))
    driver.find_element(By.CSS_SELECTOR, "input[type='text'], input[name='login']").send_keys(email_addr)
    driver.find_element(By.CSS_SELECTOR, "input[type='password']").send_keys(password)
    driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
    print("[*] Вхід у кабінет виконано")

    # 5. Пошук токена
    print("[*] Пошук токена в особистому кабінеті...")
    time.sleep(15) # Даємо час JS завантажити дані
    
    final_token = None
    page_source = driver.page_source
    # Шукаємо 16-значний буквено-цифровий код
    potential_tokens = re.findall(r'[A-Za-z0-9]{16}', page_source)
    
    for t in potential_tokens:
        if t not in ["VipPassword123", "verify-email", "registration"]:
            final_token = t
            break

    if final_token:
        print(f"[УСПІХ] ТОКЕН ЗНАЙДЕНО: {final_token}")
        
        # 6. Відправка на ваш сервер i-tv.top
        print(f"[*] Перехід на панель управління для запису...")
        driver.get(MY_PANEL_URL)
        time.sleep(5)

        # Очищення інтерфейсу від заважаючих елементів
        driver.execute_script("""
            document.querySelectorAll('#reminderOverlay, .modal-backdrop, .toast-container').forEach(el => el.remove());
            document.body.style.overflow = 'auto';
        """)

        # Знаходимо поле і вводимо токен
        input_field = wait.until(EC.presence_of_element_located((By.NAME, "input_data")))
        driver.execute_script("arguments[0].value = arguments[1];", input_field, final_token)
        
        # Сабміт форми через JS (найнадійніший метод для серверних оточень)
        driver.execute_script("document.querySelector('form').submit();")
        
        print("[+++] ДАНІ УСПІШНО ОНОВЛЕНО НА СЕРВЕРІ I-TV.TOP")
        time.sleep(5) 
    else:
        print("[-] Помилка: Токен не знайдено на сторінці.")
        driver.save_screenshot("no_token_debug.png")

except Exception as e:
    print(f"[-] Сталася помилка: {e}")
    if driver:
        driver.save_screenshot("error_state.png")

finally:
    if driver:
        driver.quit()
        print("[*] Браузер закрито")
