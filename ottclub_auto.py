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
    """Отримує нову адресу через ваш API."""
    try:
        response = requests.get(TEMP_MAIL_URL, timeout=15)
        soup = BeautifulSoup(response.text, 'html.parser')
        email_element = soup.find(id="emailText")
        return email_element.text.strip() if email_element else None
    except Exception as e:
        print(f"[-] Помилка отримання пошти: {e}")
        return None

def wait_for_otp_code(email):
    """Очікує на 6-значний код у поштовій скриньці."""
    print(f"[*] Очікуємо код для {email}...")
    pattern = r'(\d{6})' 
    for _ in range(40): 
        time.sleep(5)
        try:
            response = requests.get(f"{CHECK_MAIL_URL}?nocache={time.time()}", timeout=10)
            match = re.search(pattern, response.text)
            if match:
                return match.group(1)
        except:
            continue
    return None

# --- ЗАПУСК БРАУЗЕРА ---
options = uc.ChromeOptions()
options.add_argument("--headless") 
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")

try:
    driver = uc.Chrome(options=options, version_main=145, use_subprocess=False) 
    wait = WebDriverWait(driver, 30)

    email_addr = get_temp_email()
    if not email_addr: exit("[-] Не вдалося отримати пошту")
    print(f"[+] Пошта: {email_addr}")

    # 1. ОЧИЩЕННЯ ТА ЗАВАНТАЖЕННЯ СТОРІНКИ
    driver.get("https://www.ottclub.tv")
    time.sleep(2)
    
    print("[*] Очищення куків та сесії...")
    driver.delete_all_cookies()
    driver.execute_script("window.localStorage.clear();")
    driver.execute_script("window.sessionStorage.clear();")
    driver.refresh() # Перезавантаження для чистого стану
    time.sleep(3)

    # 2. ВВЕДЕННЯ EMAIL ТА ЗАПИТ ТЕСТУ
    email_field = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='email']")))
    email_field.send_keys(email_addr)
    time.sleep(1)

    # Гнучкий пошук кнопки (враховуємо можливу зміну мови або структури)
    try:
        test_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'ротесту')]")))
        test_btn.click()
    except:
        # Резервний метод через селектор форми
        test_btn = driver.find_element(By.CSS_SELECTOR, "form button, .btn-danger")
        driver.execute_script("arguments[0].click();", test_btn)
    
    print("[*] Запит відправлено")

    # 3. ВВЕДЕННЯ КОДУ ПІДТВЕРДЖЕННЯ
    otp_code = wait_for_otp_code(email_addr)
    if not otp_code: raise Exception("Код не отримано")
    print(f"[+] Код: {otp_code}")

    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input")))
    # Шукаємо поля для вводу коду (зазвичай 6 ячеєк)
    code_inputs = driver.find_elements(By.CSS_SELECTOR, "input[maxlength='1'], .regform input")
    if not code_inputs:
        code_inputs = driver.find_elements(By.XPATH, "//input[@type='text' or @type='number']")[0:6]

    for i, digit in enumerate(otp_code):
        code_inputs[i].send_keys(digit)
        time.sleep(0.1)

    # Обов'язкова галочка
    agreement = driver.find_element(By.CSS_SELECTOR, "input[type='checkbox']")
    driver.execute_script("arguments[0].click();", agreement)

    submit_btn = driver.find_element(By.XPATH, "//button[contains(., 'родовжити')]")
    submit_btn.click()

    # 4. ОТРИМАННЯ КЛЮЧА
    time.sleep(10)
    driver.get("https://www.ottclub.tv/billing")
    time.sleep(5)
    
    page_content = driver.page_source
    # Шукаємо ключ формату RQ55CFWG61
    key_match = re.search(r'([A-Z0-9]{10,12})', page_content)

    if key_match:
        final_key = key_match.group(1)
        print(f"[УСПІХ] КЛЮЧ: {final_key}")
        
        # ВІДПРАВКА НА СЕРВЕР
        driver.get(MY_PANEL_URL)
        time.sleep(3)
        input_field = wait.until(EC.presence_of_element_located((By.NAME, "input_data")))
        driver.execute_script("arguments[0].value = arguments[1];", input_field, final_key)
        driver.execute_script("document.querySelector('form').submit();")
        print("[+++] СИСТЕМУ ОНОВЛЕНО")
    else:
        print("[-] Ключ не знайдено на сторінці білінгу")
        driver.save_screenshot("ott_key_missing.png")

except Exception as e:
    print(f"[-] Помилка: {e}")
    driver.save_screenshot("ott_error.png")

finally:
    if 'driver' in locals():
        driver.quit()
