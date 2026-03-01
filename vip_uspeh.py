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
    """Получает новый email из вашего API."""
    session = requests.Session()
    try:
        response = session.get(TEMP_MAIL_URL, timeout=15)
        soup = BeautifulSoup(response.text, 'html.parser')
        email_element = soup.find(id="emailText")
        if email_element:
            return email_element.text.strip(), session
        return None, None
    except Exception as e:
        print(f"[-] Ошибка почтового сервиса: {e}")
        return None, None

def wait_for_activation_link(session, email):
    """Ожидает ссылку подтверждения в почтовом ящике."""
    print(f"[*] Ожидаем письмо для {email}...")
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

# --- ЗАПУСК БРАУЗЕРА ---
print("[*] Инициализация маскированного браузера (v145)...")
options = uc.ChromeOptions()
options.add_argument("--window-size=1920,1080") # Гарантирует видимость элементов

try:
    driver = uc.Chrome(options=options, version_main=145)
    wait = WebDriverWait(driver, 30)
except Exception as e:
    print(f"[-] Критическая ошибка запуска: {e}")
    exit()

try:
    # 1. Получение почты
    email_addr, py_session = get_temp_email()
    if not email_addr: 
        raise Exception("Не удалось получить временный адрес")
    
    print(f"[+] Рабочий email: {email_addr}")
    username = email_addr.split('@')[0]
    password = "VipPassword123!"

    # 2. Регистрация на Uspeh TV
    print("[*] Переход к регистрации на Uspeh TV...")
    driver.get("https://billing.uspeh.tv/register")
    time.sleep(2)
    
    wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "input[type='email']"))).send_keys(email_addr)
    driver.find_element(By.CSS_SELECTOR, "input[type='text']").send_keys(username)
    
    pass_inputs = driver.find_elements(By.CSS_SELECTOR, "input[type='password']")
    pass_inputs[0].send_keys(password)
    pass_inputs[1].send_keys(password)
    
    driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
    print("[+] Форма регистрации отправлена")

    # 3. Подтверждение почты
    activation_link = wait_for_activation_link(py_session, email_addr)
    if not activation_link:
        raise Exception("Ссылка активации не пришла")
    
    driver.get(activation_link)
    print("[+] Аккаунт успешно активирован")

    # 4. Авторизация
    wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "input[type='password']")))
    login_field = driver.find_element(By.CSS_SELECTOR, "input[type='text'], input[name='login']")
    login_field.send_keys(email_addr)
    driver.find_element(By.CSS_SELECTOR, "input[type='password']").send_keys(password)
    driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
    print("[*] Вход в личный кабинет выполнен")

    # 5. Поиск токена (Ультра-метод)
    print("[*] Поиск токена на странице (ожидание загрузки JS)...")
    time.sleep(8) 
    
    final_token = None
    page_source = driver.page_source
    # Ищем строку из 16 символов (A-Z, a-z, 0-9)
    potential_tokens = re.findall(r'[A-Za-z0-9]{16}', page_source)
    
    for t in potential_tokens:
        if t not in ["VipPassword123", "verify-email"]:
            final_token = t
            break

    if final_token:
        print(f"\n[УРА] ТОКЕН НАЙДЕН: {final_token}\n")
        
        # 6. Обновление на вашем сайте i-tv.top
        try:
            print(f"[*] Переход на i-tv.top для обновления uspeh.txt...")
            driver.get(MY_PANEL_URL)
            time.sleep(3)

            # ПРИНУДИТЕЛЬНОЕ УДАЛЕНИЕ ОВЕРЛЕЯ (блокирующего окна "Час оновити токен")
            driver.execute_script("""
                var overlay = document.getElementById('reminderOverlay');
                if(overlay) overlay.remove();
                var backdrop = document.getElementsByClassName('modal-backdrop');
                while(backdrop.length > 0) backdrop[0].remove();
            """)
            print("[!] Блокирующие элементы удалены")

            # Ввод токена через JavaScript для обхода любых блокировок
            input_field = wait.until(EC.presence_of_element_located((By.NAME, "input_data")))
            print(f"[*] Передача токена {final_token} в PHP-форму...")
            driver.execute_script("arguments[0].value = arguments[1];", input_field, final_token)
            
            # Нажатие кнопки "Оновити систему" через JavaScript
            submit_btn = driver.find_element(By.CSS_SELECTOR, "button.btn")
            driver.execute_script("arguments[0].click();", submit_btn)
            
            print("[+++] ДАННЫЕ ОТПРАВЛЕНЫ. Ожидание записи на сервере...")
            time.sleep(5) 
            
            # Проверка результата
            driver.refresh()
            time.sleep(2)
            print("[ФИНИШ] Процесс завершен. Проверьте 'Поточний стан' на сайте.")
            
        except Exception as e:
            print(f"[-] Ошибка при обновлении вашего сайта: {e}")

        # Локальное сохранение для подстраховки
        with open("uspeh_tokens.txt", "a", encoding="utf-8") as f:
            f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} | {email_addr} | {final_token}\n")
    else:
        print("[-] Ошибка: Токен не найден в коде страницы.")
        driver.save_screenshot("token_missing.png")

except Exception as e:
    print(f"[-] Произошла ошибка: {e}")
    driver.save_screenshot("final_error_debug.png")

finally:
    print("[*] Завершение через 5 секунд...")
    time.sleep(5)
    driver.quit()