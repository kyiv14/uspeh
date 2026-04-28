import time
import re
import requests
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup

# --- КОНФІГУРАЦІЯ (Твоя панель та API) ---
TEMP_MAIL_URL = "https://i-tv.top/tempmail/index.php"
CHECK_MAIL_URL = "https://i-tv.top/tempmail/check.php"
MY_PANEL_URL = "https://i-tv.top/uspeh/?tab=ottclub"

def get_temp_email():
    """Отримує нову адресу електронної пошти через твій API."""
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
    """Очікує на 6-значний код підтвердження в поштовій скриньці."""
    print(f"[*] Очікуємо на код для {email}...")
    pattern = r'\b\d{6}\b' # Шукаємо рівно 6 цифр
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
    """Налаштування для роботи на сервері (GitHub Actions)."""
    options = uc.ChromeOptions()
    options.add_argument("--headless") # Обов'язково для GitHub
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-blink-features=AutomationControlled")
    return options

# --- ЗАПУСК ---
print("[*] Ініціалізація браузера...")
driver = uc.Chrome(options=get_clean_options())
wait = WebDriverWait(driver, 40)

try:
    # 1. Перехід на сайт та очищення кукі
    driver.get("https://www.ottclub.tv/")
    driver.delete_all_cookies()
    driver.refresh()
    print("[+] Кукі очищено, сторінку оновлено.")

    # 2. Обробка модальних вікон (Screenshot 1)
    try:
        # Приймаємо кукі (Синя кнопка)
        accept_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Принять все')]")))
        accept_btn.click()
        print("[+] Кукі прийнято.")
        
        # Закриваємо банер мобільного застосунку (Крестик)
        # Використовуємо універсальний шлях для хрестика (SVG або клас close)
        close_x = wait.until(EC.element_to_be_clickable((By.XPATH, "//*[local-name()='svg' and contains(@class, 'close')] | //*[contains(@class, 'modal-close')] | //div[contains(@class, 'close')]")))
        close_x.click()
        print("[+] Рекламний банер закрито.")
    except Exception as e:
        print(f"[!] Модалки не знайдено або вже закрито.")

    # 3. Реєстрація (Screenshot 2)
    email_addr, py_session = get_temp_email()
    if not email_addr: raise Exception("Не вдалося отримати пошту")
    
    print(f"[+] Використовуємо: {email_addr}")
    
    email_field = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='email']")))
    email_field.clear()
    email_field.send_keys(email_addr)
    
    # Кнопка "Протестувати 3 дні безкоштовно"
    test_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Протестувати')]")))
    test_btn.click()

    # 4. Чекбокс та Код (Screenshot 4, 5)
    # Погодження з умовами (Чекбокс часто потребує JS кліку, якщо перекритий)
    check_box = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='checkbox']")))
    if not check_box.is_selected():
        driver.execute_script("arguments[0].click();", check_box)
    print("[+] Чекбокс активовано.")

    # Очікування коду через твій API
    otp = wait_for_otp_code(py_session, email_addr)
    if not otp: raise Exception("Код не отримано вчасно")
    print(f"[+] Отримано код: {otp}")

    # Введення коду в 6 ячейок (Screenshot 5)
    # Зазвичай це масив інпутів у формі reg-form
    code_inputs = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".reg-form input[type='text'], input[class*='code']")))
    for i, char in enumerate(otp):
        code_inputs[i].send_keys(char)
    
    # Кнопка "Продовжити"
    continue_btn = driver.find_element(By.XPATH, "//button[contains(., 'Продовжити')]")
    continue_btn.click()
    print("[*] Код введено. Перехід до кабінету...")

    # 5. Отримання Ключа (Screenshot 8, 9)
    # Чекаємо завантаження кабінету та тиснемо на профіль (верхній правий кут)
    # Часто це елемент з класом .icon-user або посиланням на billing
    profile_btn = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "a[href*='billing'], .icon-user, .user-menu, .header__user")))
    profile_btn.click()
    print("[*] Відкрито налаштування профілю.")
    
    # Отримуємо текст ключа з модального вікна "Налаштування профілю"
    # Шукаємо div, який іде після тексту "Ключ"
    key_element = wait.until(EC.presence_of_element_located((By.XPATH, "//div[contains(text(), 'Ключ')]/following-sibling::div | //input[@id='api-key']")))
    ott_key = key_element.text.strip() if key_element.tag_name != 'input' else key_element.get_attribute('value')
    
    if not ott_key or len(ott_key) < 5:
        raise Exception("Ключ пустий або не знайдений у профілі")
    
    print(f"[УСПІХ] КЛЮЧ ЗНАЙДЕНО: {ott_key}")

    # 6. Оновлення на твоєму сайті (Screenshot 10)
    driver.get(MY_PANEL_URL)
    time.sleep(5)

    # Очистка можливих накладень (overlays), щоб вони не заважали кліку
    driver.execute_script("""
        document.querySelectorAll('.modal-backdrop, #reminderOverlay, .toast').forEach(el => el.remove());
        document.body.style.overflow = 'auto';
    """)

    # Знаходимо поле для вставки токена
    # На основі Screenshot 10, шукаємо інпут всередині форми
    input_field = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[placeholder*='токен'], input[name='input_data']")))
    input_field.clear()
    
    # Використовуємо JS для вставки, щоб уникнути проблем з фокусом
    driver.execute_script("arguments[0].value = arguments[1];", input_field, ott_key)
    
    # Натискаємо "ОНОВИТИ СИСТЕМУ"
    # Можна через submit форми для надійності
    try:
        update_btn = driver.find_element(By.XPATH, "//button[contains(., 'ОНОВИТИ')]")
        update_btn.click()
    except:
        driver.execute_script("document.querySelector('form').submit();")
    
    print("[+++] ДАНІ УСПІШНО ВІДПРАВЛЕНО НА СЕРВЕР")
    time.sleep(5) 

except Exception as e:
    print(f"[-] Критична помилка: {e}")
    driver.save_screenshot("debug_error.png") # Збереження доказу для GitHub Actions

finally:
    driver.quit()
    print("[*] Роботу браузера завершено.")
