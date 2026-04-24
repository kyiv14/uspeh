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

def get_clean_options():
    """Створює новий об'єкт опцій для кожної спроби запуску."""
    options = uc.ChromeOptions()
    options.add_argument("--headless") 
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-blink-features=AutomationControlled")
    return options

# --- ЗАПУСК БРАУЗЕРА (ВИПРАВЛЕНО ДЛЯ ВЕРСІЇ 147) ---
print("[*] Ініціалізація маскованого браузера...")

driver = None
# Вказуємо версію 147, яку зараз використовує GitHub
CURRENT_CHROME_VERSION = 147 

try:
    # Спроба №1: З явною вказівкою версії 147
    driver = uc.Chrome(
        options=get_clean_options(), 
        version_main=CURRENT_CHROME_VERSION,
        use_subprocess=True
    ) 
    wait = WebDriverWait(driver, 40)
except Exception as e:
    print(f"[*] Спроба №1 (v{CURRENT_CHROME_VERSION}) не вдалася: {e}")
    try:
        # Спроба №2: Автоматичний підбір драйвера
        driver = uc.Chrome(options=get_clean_options(), use_subprocess=True)
        wait = WebDriverWait(driver, 40)
    except Exception as e2:
        print(f"[-] Критична помилка запуску: {e2}")
        exit(1)

try:
    # 1. Реєстрація на Uspeh TV
    email_addr, py_session = get_temp_email()
    if not email_addr: 
        raise Exception("Не вдалося отримати тимчасову пошту")
    
    print(f"[+] Використовуємо пошту: {email_addr}")
    username = email_addr.split('@')[0]
    password = "VipPassword123!"

    driver.get("https://billing.uspeh.tv/register")
    time.sleep(5)
    
    wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "input[type='email']"))).send_keys(email_addr)
    driver.find_element(By.CSS_SELECTOR, "input[type='text']").send_keys(username)
    
    pass_inputs = driver.find_elements(By.CSS_SELECTOR, "input[type='password']")
    pass_inputs[0].send_keys(password)
    pass_inputs[1].send_keys(password)
    
    driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
    print("[*] Реєстрація відправлена. Чекаємо на активацію...")

    # 2. Активація через посилання
    activation_link = wait_for_activation_link(py_session, email_addr)
    if not activation_link:
        raise Exception("Лист активації не знайдено")
    
    driver.get(activation_link)
    print("[+] Аккаунт активовано")
    time.sleep(3)

    # 3. Авторизація
    wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "input[type='password']")))
    driver.find_element(By.CSS_SELECTOR, "input[type='text'], input[name='login']").send_keys(email_addr)
    driver.find_element(By.CSS_SELECTOR, "input[type='password']").send_keys(password)
    driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
    print("[*] Вхід виконано")

    # 4. Пошук токена
    print("[*] Очікуємо завантаження токена (15 сек)...")
    time.sleep(15) 
    
    final_token = None
    page_source = driver.page_source
    potential_tokens = re.findall(r'[A-Za-z0-9]{16}', page_source)
    
    for t in potential_tokens:
        if t not in ["VipPassword123", "verify-email", "registration"]:
            final_token = t
            break

    if final_token:
        print(f"[УСПІХ] ТОКЕН ЗНАЙДЕНО: {final_token}")
        
        # 5. Оновлення на вашому сайті i-tv.top
        driver.get(MY_PANEL_URL)
        time.sleep(5)

        # Очищення інтерфейсу перед відправкою
        driver.execute_script("""
            document.querySelectorAll('#reminderOverlay, .modal-backdrop, .toast-container').forEach(el => el.remove());
            document.body.style.overflow = 'auto';
        """)

        input_field = wait.until(EC.presence_of_element_located((By.NAME, "input_data")))
        driver.execute_script("arguments[0].value = arguments[1];", input_field, final_token)
        
        # Прямий submit через JS для надійності
        driver.execute_script("document.querySelector('form').submit();")
        
        print("[+++] ДАНІ ВІДПРАВЛЕНО НА СЕРВЕР")
        time.sleep(5) 
    else:
        print("[-] Помилка: Токен не знайдено.")
        driver.save_screenshot("token_missing.png")

except Exception as e:
    print(f"[-] Сталася помилка: {e}")
    if driver:
        driver.save_screenshot("error_debug.png")

finally:
    if driver:
        driver.quit()
