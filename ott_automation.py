import time
import re
import requests
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
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
    for _ in range(60): 
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
    # Емуляція мобільного екрану, як на скріншотах
    options.add_argument("--window-size=375,812") 
    options.add_argument("--user-agent=Mozilla/5.0 (iPhone; CPU iPhone OS 13_2_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/13.0.3 Mobile/15E148 Safari/604.1")
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
wait = WebDriverWait(driver, 45)

try:
    # 1. Завантаження сайту
    driver.get("https://www.ottclub.tv/")
    driver.delete_all_cookies()
    driver.refresh()
    time.sleep(8)
    print("[+] Сайт завантажено.")

    # 2. Агресивне видалення перешкод (кукі та банери) через JS
    driver.execute_script("""
        var selectors = [
            '.cookie-banner', '#cookie-popup', '[class*="cookie"]', 
            '.modal', '.overlay', '[class*="close"]', 'button[id*="accept"]'
        ];
        selectors.forEach(s => {
            document.querySelectorAll(s).forEach(el => el.remove());
        });
        document.body.style.overflow = 'auto';
    """)
    print("[*] Сторінку очищено від банерів.")

    # 3. Реєстрація
    email_addr, py_session = get_temp_email()
    if not email_addr: raise Exception("Пошта не отримана")
    print(f"[+] Пошта: {email_addr}")
    
    # Введення пошти через JS для надійності
    email_input = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='email']")))
    driver.execute_script("arguments[0].value = arguments[1];", email_input, email_addr)
    email_input.send_keys(" ") # Тригер для валідації форми
    
    # Кнопка відправки
    submit_btn = wait.until(EC.presence_of_element_located((By.XPATH, "//button[contains(., 'Протесту')] | //form//button[@type='submit']")))
    driver.execute_script("arguments[0].click();", submit_btn)
    print("[*] Форму відправлено.")

    # 4. Чекбокс та Код (Screenshot 3)
    time.sleep(5)
    try:
        # Клікаємо чекбокс прийняття умов
        checkbox = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='checkbox']")))
        driver.execute_script("arguments[0].click();", checkbox)
        print("[+] Чекбокс активовано.")
    except: pass

    otp = wait_for_otp_code(py_session, email_addr)
    if not otp: raise Exception("Код не прийшов.")
    print(f"[+] Код: {otp}")

    # Введення коду в ячейки
    code_fields = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "input[class*='code'], .reg-form input")))
    for i, char in enumerate(otp):
        code_fields[i].send_keys(char)
    
    # Натискаємо "Продовжити"
    continue_btn = driver.find_element(By.XPATH, "//button[contains(., 'Продов')] | //button[contains(., 'Продо')]")
    driver.execute_script("arguments[0].click();", continue_btn)

    # 5. Отримання Ключа
    time.sleep(8)
    driver.get("https://www.ottclub.tv/billing") # Прямий перехід в білінг
    time.sleep(5)
    
    # Пошук ключа за структурою
    key_el = wait.until(EC.presence_of_element_located((By.XPATH, "//div[contains(text(), 'Ключ')]/following-sibling::div | //input[@id='api-key']")))
    final_key = key_el.text.strip() if key_el.tag_name != 'input' else key_el.get_attribute('value')
    
    if not final_key:
        final_key = re.search(r'[A-Z0-9]{8,16}', driver.page_source).group(0)

    print(f"[УСПІХ] КЛЮЧ: {final_key}")

    # 6. Оновлення i-tv.top
    driver.get(MY_PANEL_URL)
    time.sleep(5)
    
    # Видалення заважаючих елементів на i-tv.top
    driver.execute_script("document.querySelectorAll('.modal-backdrop, #reminderOverlay').forEach(el => el.remove());")
    
    token_field = wait.until(EC.presence_of_element_located((By.NAME, "input_data")))
    driver.execute_script("arguments[0].value = arguments[1];", token_field, final_key)
    driver.execute_script("document.querySelector('form').submit();")
    
    print("[+++] ДАНІ ВІДПРАВЛЕНО")
    time.sleep(5) 

except Exception as e:
    print(f"[-] Помилка: {str(e)}")
    traceback.print_exc()
    driver.save_screenshot("debug_error.png")

finally:
    driver.quit()
    print("[*] Завершено.")
