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
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-blink-features=AutomationControlled")
    # Додаємо User-Agent, щоб сайт не блокував бота
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36")
    return options

# --- ЗАПУСК ---
print("[*] Ініціалізація браузера...")
CURRENT_CHROME_VERSION = 147 

driver = uc.Chrome(
    options=get_clean_options(), 
    version_main=CURRENT_CHROME_VERSION,
    use_subprocess=True
)
wait = WebDriverWait(driver, 40) # Збільшено час очікування

try:
    # 1. Завантаження сайту
    driver.get("https://www.ottclub.tv/")
    driver.delete_all_cookies()
    driver.refresh()
    time.sleep(5)
    print("[+] Сторінку завантажено.")

    # 2. Закриття модальних вікон
    try:
        # Прийняти кукі
        cookie_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Принять')] | //button[contains(., 'Прийняти')] | //button[contains(@class, 'cookie')]")))
        cookie_btn.click()
        print("[+] Кукі прийнято.")
    except:
        print("[!] Кнопка кукі не знайдена.")

    try:
        # Закрити рекламний банер (Screenshot 1)
        close_x = wait.until(EC.element_to_be_clickable((By.XPATH, "//*[contains(@class, 'close')] | //*[local-name()='svg' and contains(@class, 'close')]")))
        driver.execute_script("arguments[0].click();", close_x)
        print("[+] Рекламний банер закрито.")
    except:
        print("[!] Банер не знайдено.")

    # 3. Реєстрація
    email_addr, py_session = get_temp_email()
    if not email_addr: raise Exception("Пошта не отримана")
    print(f"[+] Пошта: {email_addr}")
    
    # Пошук поля вводу
    email_field = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='email'], input[name='email']")))
    email_field.clear()
    email_field.send_keys(email_addr)
    
    # Пошук кнопки через кілька варіантів (більш надійно)
    try:
        test_btn = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button.btn-primary, button[type='submit'], .registration-form button")))
        test_btn.click()
    except:
        # Якщо селектори не спрацювали, клікаємо по кнопці з будь-яким текстом у формі
        test_btn = driver.find_element(By.XPATH, "//form//button")
        driver.execute_script("arguments[0].click();", test_btn)
    
    print("[*] Форма відправлена.")

    # 4. Чекбокс та Код
    # Очікуємо появи чекбокса (Угода)
    check_box = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='checkbox']")))
    driver.execute_script("arguments[0].click();", check_box)
    print("[+] Чекбокс активовано.")

    otp = wait_for_otp_code(py_session, email_addr)
    if not otp: raise Exception("Код не знайдено")
    print(f"[+] Код: {otp}")

    # Введення 6 цифр коду
    code_inputs = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "input[class*='code'], .reg-form input")))
    for i, char in enumerate(otp):
        code_inputs[i].send_keys(char)
    
    # Кнопка "Продовжити"
    continue_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Продо')] | //button[contains(., 'Продов')]")))
    driver.execute_script("arguments[0].click();", continue_btn)

    # 5. Отримання Ключа
    # Очікуємо завантаження кабінету і клікаємо профіль
    profile_btn = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "a[href*='billing'], .icon-user, .user-menu")))
    profile_btn.click()
    
    # Виймаємо ключ
    key_element = wait.until(EC.presence_of_element_located((By.XPATH, "//div[contains(text(), 'Ключ')]/following-sibling::div | //input[@id='api-key']")))
    ott_key = key_element.text.strip() if key_element.tag_name != 'input' else key_element.get_attribute('value')
    
    if not ott_key: raise Exception("Ключ не знайдено")
    print(f"[УСПІХ] КЛЮЧ: {ott_key}")

    # 6. Оновлення i-tv.top
    driver.get(MY_PANEL_URL)
    time.sleep(5)
    driver.execute_script("document.querySelectorAll('.modal-backdrop, #reminderOverlay').forEach(el => el.remove());")
    
    input_field = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[name='input_data'], input[placeholder*='токен']")))
    driver.execute_script("arguments[0].value = arguments[1];", input_field, ott_key)
    
    driver.execute_script("document.querySelector('form').submit();")
    print("[+++] ГОТОВО: ДАНІ ВІДПРАВЛЕНО")
    time.sleep(5) 

except Exception as e:
    print(f"[-] Помилка: {str(e)}")
    traceback.print_exc()
    driver.save_screenshot("debug_error.png")

finally:
    driver.quit()
    print("[*] Кінець роботи.")
