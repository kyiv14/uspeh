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

# --- ЗАПУСК БРАУЗЕРА (ВИПРАВЛЕНО ДЛЯ КОНФЛІКТУ ВЕРСІЙ 145/146 НА GITHUB) ---
print("[*] Ініціалізація маскованого браузера...")

options = uc.ChromeOptions()
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--disable-gpu")
options.add_argument("--window-size=1920,1080")

try:
    # Примусово вказуємо версію 145 для сумісності з поточним середовищем GitHub
    # use_subprocess=False усуває помилку "cannot connect to chrome"
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
    # 1. Реєстрація на Uspeh TV
    email_addr, py_session = get_temp_email()
    if not email_addr: 
        raise Exception("Не вдалося отримати тимчасову пошту")
    
    print(f"[+] Використовуємо пошту: {email_addr}")
    username = email_addr.split('@')[0]
    password = "VipPassword123!"

    driver.get("https://billing.uspeh.tv/register")
    time.sleep(2)
    
    wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "input[type='email']"))).send_keys(email_addr)
    driver.find_element(By.CSS_SELECTOR, "input[type='text']").send_keys(username)
    
    pass_inputs = driver.find_elements(By.CSS_SELECTOR, "input[type='password']")
    pass_inputs[0].send_keys(password)
    pass_inputs[1].send_keys(password)
    
    driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
    print("[*] Форму реєстрації відправлено")

    # 2. Активація через посилання
    activation_link = wait_for_activation_link(py_session, email_addr)
    if not activation_link:
        raise Exception("Лист активації не знайдено")
    
    driver.get(activation_link)
    print("[+] Аккаунт активовано")

    # 3. Авторизація
    wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "input[type='password']")))
    driver.find_element(By.CSS_SELECTOR, "input[type='text'], input[name='login']").send_keys(email_addr)
    driver.find_element(By.CSS_SELECTOR, "input[type='password']").send_keys(password)
    driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
    print("[*] Вхід виконано")

    # 4. Пошук токена (Сканування коду сторінки)
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
        
        # 5. Оновлення на вашому сайті i-tv.top
        print(f"[*] Перехід на i-tv.top для запису в uspeh.txt...")
        driver.get(MY_PANEL_URL)
        time.sleep(5)

        # Видалення оверлеїв через JS, щоб не заважали формі
        driver.execute_script("""
            document.querySelectorAll('#reminderOverlay, .modal-backdrop, .toast-container').forEach(el => el.remove());
            document.body.style.overflow = 'auto';
        """)

        # Введення токена та відправка форми
        input_field = wait.until(EC.presence_of_element_located((By.NAME, "input_data")))
        driver.execute_script("arguments[0].value = arguments[1];", input_field, final_token)
        
        # Використовуємо прямий submit форми для надійності на HostiQ
        driver.execute_script("document.querySelector('form').submit();")
        
        print("[+++] ДАНІ ВІДПРАВЛЕНО НА ВАШ СЕРВЕР")
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
