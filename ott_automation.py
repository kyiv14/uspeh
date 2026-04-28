import time
import re
import requests
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from bs4 import BeautifulSoup
import traceback

# --- КОНФІГУРАЦІЯ ---
TEMP_MAIL_URL = "https://i-tv.top/tempmail/index.php"
CHECK_MAIL_URL = "https://i-tv.top/tempmail/check.php"
MY_PANEL_URL = "https://i-tv.top/uspeh/?tab=ottclub"

def get_temp_email():
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

def wait_for_otp_code(session, email):
    print(f"[*] Очікуємо на код для {email}...")
    pattern = r'\b\d{6}\b'
    # Збільшуємо час очікування до 7 хвилин (84 спроби по 5 сек)
    for _ in range(84): 
        time.sleep(5)
        try:
            response = session.get(f"{CHECK_MAIL_URL}?lang=ru&nocache={time.time()}", timeout=10)
            code_match = re.search(pattern, response.text)
            if code_match:
                return code_match.group(0)
        except:
            continue
    return None

def get_clean_options():
    options = uc.ChromeOptions()
    options.add_argument("--headless") 
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1280,1024")
    options.add_argument("--disable-blink-features=AutomationControlled")
    return options

# --- ЗАПУСК ---
print("[*] Ініціалізація браузера...")
CURRENT_CHROME_VERSION = 147 

driver = uc.Chrome(
    options=get_clean_options(), 
    version_main=CURRENT_CHROME_VERSION,
    use_subprocess=True
)
wait = WebDriverWait(driver, 50)

try:
    # 1. Завантаження сайту
    driver.get("https://www.ottclub.tv/")
    driver.delete_all_cookies()
    driver.refresh()
    time.sleep(10)
    print("[+] Сайт завантажено.")

    # 2. Очищення сторінки
    driver.execute_script("document.querySelectorAll('.modal, .cookie-banner, .overlay, [class*=\"close\"]').forEach(el => el.remove());")

    # 3. Реєстрація
    email_addr, py_session = get_temp_email()
    if not email_addr: raise Exception("Пошта не отримана")
    print(f"[+] Пошта: {email_addr}")
    
    email_input = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='email']")))
    email_input.clear()
    email_input.send_keys(email_addr)
    time.sleep(2)
    
    # СПРОБА 1: Клік по кнопці через JS
    try:
        submit_btn = driver.find_element(By.XPATH, "//button[contains(., 'Протесту')] | //form//button")
        driver.execute_script("arguments[0].click();", submit_btn)
        print("[*] Кнопку натиснуто через JS.")
    except:
        # СПРОБА 2: Натискання ENTER
        email_input.send_keys(Keys.ENTER)
        print("[*] Дані відправлено через ENTER.")

    # 4. Чекбокс та Код
    time.sleep(8) # Даємо сайту час подумати
    try:
        checkbox = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='checkbox']")))
        driver.execute_script("arguments[0].click();", checkbox)
        print("[+] Чекбокс активовано.")
    except: pass

    otp = wait_for_otp_code(py_session, email_addr)
    if not otp: 
        # Якщо код не знайдено, зробимо скріншот форми, можливо там помилка "Email вже існує"
        driver.save_screenshot("no_code_error.png")
        raise Exception("Код не знайдено.")
    
    print(f"[+] Отримано код: {otp}")

    # Введення коду
    code_fields = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "input[type='text'], input[class*='code']")))
    for i, char in enumerate(otp):
        if i < len(code_fields):
            code_fields[i].send_keys(char)
    
    time.sleep(2)
    code_fields[-1].send_keys(Keys.ENTER)
    print("[*] Код підтверджено.")

    # 5. Отримання Ключа
    time.sleep(12)
    driver.get("https://www.ottclub.tv/billing")
    time.sleep(6)
    
    key_el = wait.until(EC.presence_of_element_located((By.XPATH, "//div[contains(text(), 'Ключ')]/following-sibling::div | //input[@id='api-key']")))
    final_key = key_el.text.strip() if key_el.tag_name != 'input' else key_el.get_attribute('value')
    
    if not final_key:
        match = re.search(r'[A-Z0-9]{10,16}', driver.page_source)
        if match: final_key = match.group(0)

    print(f"[УСПІХ] КЛЮЧ: {final_key}")

    # 6. Оновлення i-tv.top
    driver.get(MY_PANEL_URL)
    time.sleep(5)
    driver.execute_script("document.querySelectorAll('.modal-backdrop, #reminderOverlay').forEach(el => el.remove());")
    
    token_field = wait.until(EC.presence_of_element_located((By.NAME, "input_data")))
    driver.execute_script("arguments[0].value = arguments[1];", token_field, final_key)
    driver.execute_script("document.querySelector('form').submit();")
    
    print("[+++] ДАНІ ВІДПРАВЛЕНО НА СЕРВЕР")
    time.sleep(5) 

except Exception as e:
    print(f"[-] Помилка: {str(e)}")
    traceback.print_exc()
    driver.save_screenshot("debug_error.png")

finally:
    driver.quit()
    print("[*] Завершено.")
