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
MY_PANEL_URL = "https://i-tv.top/uspeh/?tab=uspeh" # Ваш обробник для збереження ключа

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
    pattern = r'(\d{6})' # Шукаємо рівно 6 цифр
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
options.add_argument("--headless") # Для GitHub Actions
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")

try:
    # Використовуємо стабільні налаштування для середовища GitHub
    driver = uc.Chrome(options=options, version_main=145, use_subprocess=False) 
    wait = WebDriverWait(driver, 30)

    email_addr = get_temp_email()
    if not email_addr: exit("[-] Не вдалося отримати пошту")
    print(f"[+] Використовуємо: {email_addr}")

    # 1. Головна сторінка та запит на тест
    driver.get("https://www.ottclub.tv")
    email_field = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='email']")))
    email_field.send_keys(email_addr)
    
    # Натискаємо кнопку тесту
    test_btn = driver.find_element(By.XPATH, "//button[contains(., 'Протестувати')]")
    test_btn.click()

    # 2. Введення коду підтвердження
    otp_code = wait_for_otp_code(email_addr)
    if not otp_code: raise Exception("Код не знайдено в пошті")
    print(f"[+] Код отримано: {otp_code}")

    # Знаходимо 6 полів для цифр
    # На сайті вони зазвичай мають спільний клас або тип number/text
    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input")))
    code_inputs = driver.find_elements(By.CSS_SELECTOR, "div[class*='regform'] input, input[maxlength='1']")
    
    if len(code_inputs) < 6:
        # Резервний метод пошуку полів
        code_inputs = driver.find_elements(By.XPATH, "//input[@type='text' or @type='number']")[0:6]

    for i, digit in enumerate(otp_code):
        code_inputs[i].send_keys(digit)
        time.sleep(0.1)

    # Приймаємо умови (обов'язково для активації кнопки)
    agreement = driver.find_element(By.CSS_SELECTOR, "input[type='checkbox']")
    if not agreement.is_selected():
        driver.execute_script("arguments[0].click();", agreement)

    # Натискаємо "Продовжити"
    submit_btn = driver.find_element(By.XPATH, "//button[contains(., 'Продовжити')]")
    submit_btn.click()

    # 3. Отримання ключа
    print("[*] Перехід до профілю...")
    time.sleep(8) # Чекаємо на створення аккаунту
    driver.get("https://www.ottclub.tv/billing")
    
    # Шукаємо Ключ (формат: RQ55CFWG61)
    time.sleep(5)
    page_content = driver.page_source
    # Регулярний вираз для пошуку ключа (10-12 символів: великі літери та цифри)
    key_match = re.search(r'([A-Z0-9]{10,12})', page_content)

    if key_match:
        final_key = key_match.group(1)
        print(f"[УСПІХ] КЛЮЧ OTT: {final_key}")
        
        # 4. Відправка на ваш сервер
        driver.get(MY_PANEL_URL)
        time.sleep(5)
        # Видаляємо можливі банери
        driver.execute_script("document.querySelectorAll('.modal-backdrop').forEach(el => el.remove());")
        
        input_data = wait.until(EC.presence_of_element_located((By.NAME, "input_data")))
        driver.execute_script("arguments[0].value = arguments[1];", input_data, final_key)
        driver.execute_script("document.querySelector('form').submit();")
        print("[+++] КЛЮЧ ОНОВЛЕНО НА СЕРВЕРІ")
    else:
        print("[-] Не вдалося знайти ключ на сторінці")
        driver.save_screenshot("ott_key_error.png")

except Exception as e:
    print(f"[-] Сталася помилка: {e}")
    driver.save_screenshot("ott_fatal.png") #

finally:
    if 'driver' in locals():
        driver.quit()

