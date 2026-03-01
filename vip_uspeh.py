import time
import re
import requests
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup

# --- НАСТРОЙКИ ВАШИХ ПРОЕКТОВ ---
TEMP_MAIL_URL = "https://i-tv.top/tempmail/index.php"
CHECK_MAIL_URL = "https://i-tv.top/tempmail/check.php"
MY_PANEL_URL = "https://i-tv.top/uspeh/?tab=uspeh"

def get_temp_email():
    """Отримує новий email з вашого API."""
    session = requests.Session()
    try:
        response = session.get(TEMP_MAIL_URL, timeout=15)
        soup = BeautifulSoup(response.text, 'html.parser')
        email_element = soup.find(id="emailText")
        if email_element:
            return email_element.text.strip(), session
        return None, None
    except Exception as e:
        print(f"[-] Помилка поштового сервісу: {e}")
        return None, None

def wait_for_activation_link(session, email):
    """Очікує посилання підтвердження в поштовій скриньці."""
    print(f"[*] Очікуємо лист для {email}...")
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

# --- ЗАПУСК БРАУЗЕРА (ОПТИМІЗОВАНО ДЛЯ GITHUB ACTIONS) ---
print("[*] Ініціалізація маскованого браузера для GitHub...")
options = uc.ChromeOptions()
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--disable-gpu")
options.add_argument("--window-size=1920,1080")

try:
    # Використовуємо headless режим прямо в конструкторі для стабільності
    driver = uc.Chrome(options=options, headless=True, use_subprocess=False) 
    wait = WebDriverWait(driver, 30)
except Exception as e:
    print(f"[-] Критична помилка запуску: {e}")
    exit()

try:
    # 1. Отримання пошти
    email_addr, py_session = get_temp_email()
    if not email_addr: 
        raise Exception("Не вдалося отримати тимчасову адресу")
    
    print(f"[+] Робочий email: {email_addr}")
    username = email_addr.split('@')[0]
    password = "VipPassword123!"

    # 2. Реєстрація на Uspeh TV
    print("[*] Перехід до реєстрації на Uspeh TV...")
    driver.get("https://billing.uspeh.tv/register")
    time.sleep(2)
    
    wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "input[type='email']"))).send_keys(email_addr)
    driver.find_element(By.CSS_SELECTOR, "input[type='text']").send_keys(username)
    
    pass_inputs = driver.find_elements(By.CSS_SELECTOR, "input[type='password']")
    pass_inputs[0].send_keys(password)
    pass_inputs[1].send_keys(password)
    
    driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
    print("[+] Форма реєстрації відправлена")

    # 3. Підтвердження пошти
    activation_link = wait_for_activation_link(py_session, email_addr)
    if not activation_link:
        raise Exception("Посилання активації не прийшло")
    
    driver.get(activation_link)
    print("[+] Аккаунт успішно активовано")

    # 4. Авторизація
    wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "input[type='password']")))
    login_field = driver.find_element(By.CSS_SELECTOR, "input[type='text'], input[name='login']")
    login_field.send_keys(email_addr)
    driver.find_element(By.CSS_SELECTOR, "input[type='password']").send_keys(password)
    driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
    print("[*] Вхід у особистий кабінет виконано")

    # 5. Пошук токена (Ультра-метод сканування коду)
    print("[*] Пошук токена на сторінці (очікування завантаження JS)...")
    time.sleep(12) # Збільшена пауза для стабільності в хмарі
    
    final_token = None
    page_source = driver.page_source
    # Шукаємо 16-значний код (A-Z, a-z, 0-9)
    potential_tokens = re.findall(r'[A-Za-z0-9]{16}', page_source)
    
    for t in potential_tokens:
        if t not in ["VipPassword123", "verify-email"]:
            final_token = t
            break

    if final_token:
        print(f"\n[УРА] ТОКЕН ЗНАЙДЕНО: {final_token}\n")
        
        # 6. Оновлення на вашому сайті i-tv.top
        try:
            print(f"[*] Перехід на i-tv.top для оновлення...")
            driver.get(MY_PANEL_URL)
            time.sleep(5)

            # ПРИМУСОВЕ ВИДАЛЕННЯ ОВЕРЛЕЮ ТА МОДАЛОК
            driver.execute_script("""
                document.querySelectorAll('#reminderOverlay, .modal-backdrop, .toast-container').forEach(el => el.remove());
                document.body.style.overflow = 'auto';
            """)
            print("[!] Блокуючі елементи видалено")

            # Введення токена через JavaScript
            input_field = wait.until(EC.presence_of_element_located((By.NAME, "input_data")))
            print(f"[*] Відправка токена {final_token} у форму...")
            driver.execute_script("arguments[0].value = arguments[1];", input_field, final_token)
            
            # Пряма відправка форми через JS submit() — найнадійніший метод
            driver.execute_script("document.querySelector('form').submit();")
            
            print("[+++] ДАНІ ВІДПРАВЛЕНО НА СЕРВЕР")
            time.sleep(5) 
            
        except Exception as e:
            print(f"[-] Помилка при оновленні вашого сайту: {e}")
            driver.save_screenshot("itv_error.png")

    else:
        print("[-] Помилка: Токен не знайдено в коді сторінки.")
        driver.save_screenshot("token_missing_debug.png")

except Exception as e:
    print(f"[-] Сталася помилка: {e}")
    driver.save_screenshot("final_error.png")

finally:
    print("[*] Завершення сесії...")
    driver.quit()
