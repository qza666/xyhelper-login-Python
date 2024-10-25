import requests
import json
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

def process_browser_log_entry(entry):
    try:
        response = json.loads(entry['message'])['message']
        return response
    except:
        return None

def get_session_id(code, code_verifier):
    url = 'https://login.closeai.biz/api/getsession'
    data = {
        'location': f'com.openai.chat://auth0.openai.com/ios/com.openai.chat/callback?code={code}',
        'codeVerifier': code_verifier
    }
    try:
        response = requests.post(url, json=data)
        response.raise_for_status()
        session_id = response.json()
        
        access_token = session_id.get('accessToken', '未找到accessToken')
        refresh_token = session_id.get('refresh_token', '未找到refresh_token')
        
        return session_id, access_token, refresh_token
    except Exception as e:
        print(f"获取会话时出错: {e}")
        return None, None, None

def login_and_get_code(driver, login_url, email, password, max_retries=3):
    for attempt in range(max_retries):
        driver.get(login_url)
        
        try:
            WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.CLASS_NAME, 'email-or-phone-input'))).send_keys(email)
            WebDriverWait(driver, 20).until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'button.continue-btn'))).click()
            WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'input[type="password"]'))).send_keys(password)
            WebDriverWait(driver, 20).until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[type="submit"]'))).click()

            time.sleep(5)

            browser_log = driver.get_log('performance')
            events = [process_browser_log_entry(entry) for entry in browser_log]
            
            for event in events:
                if event and 'params' in event and 'request' in event['params']:
                    request_url = event['params']['request']['url']
                    if 'code=' in request_url:
                        return request_url.split('code=')[1].split('&')[0]
            
            print(f"尝试 {attempt + 1}: 未找到代码，刷新页面...")
        except Exception as e:
            print(f"尝试 {attempt + 1} 失败: {e}")
        
        if attempt < max_retries - 1:
            time.sleep(5)  # 在重试之前等待
    
    print("达到最大重试次数，未能获取代码")
    return None

def update_backend(email, password, session_id, car_id):
    url = "https://trtrc.com/admin/chatgpt/session/add"
    # 这里把trtrc.com改为你自己的ChatGPT域名，例如：chatgpt.com

    payload = json.dumps({
        "sort": 0,
        "carID": car_id,
        "email": email,
        "password": password,
        "status": 0,
        "isPlus": 0,
        "officialSession": session_id
    })

    headers = {
        'User-Agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
        'Accept': "application/json, text/plain, */*",
        'Content-Type': "application/json",
        'Accept-Language': "zh-CN,zh;q=0.9",
        'Authorization': "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc1JlZnJlc2giOmZhbHNlLCJyb2xlSWRzIjpbIjEiXSwidXNlcm5hbWUiOiJxemE2NjY2NjYiLCJ1c2VySWQiOjEsInBhc3N3b3JkVmVyc2lvbiI6NCwiZXhwIjoxNzI5Mzc0MDc4LCJpYXQiOjE3MjkzNjY4Nzh9.tpoOFxxxxxxxxxxxx"
        #Authorization改为你ChatGPT后台的token，你可以在cookie中寻找到
    }

    response = requests.post(url, data=payload, headers=headers)
    return response.text

def read_accounts_from_file(file_path):
    accounts = []
    with open(file_path, 'r') as file:
        for line in file:
            email, password = line.strip().split('\t')
            accounts.append({"email": email, "password": password})
    return accounts

def main():
    accounts = read_accounts_from_file(r"D:\Backup\Downloads\Telegram Desktop\extracted_accounts.txt") 
    #这里改为你账号所在的文本位置，
    # 文本的格式为：账号+tab+密码 ，一行一个账号
    #列如：abc@gmail.com    123456789
    

    options = webdriver.ChromeOptions()
    options.add_experimental_option("detach", True)
    options.set_capability('goog:loggingPrefs', {'performance': 'ALL'})
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

    car_id_counter = 1

    try:
        for account in accounts:
            response = requests.get('https://login.closeai.biz/gptlogin')
            response.raise_for_status()
            data = response.json()
            login_url, code_verifier = data['loginurl'], data['codeVerifier']

            code = login_and_get_code(driver, login_url, account['email'], account['password'])

            if code:
                session_id, access_token, refresh_token = get_session_id(code, code_verifier)
                print(f"账户: {account['email']}")
                print(f"会话ID: {session_id}")
                print(f"访问令牌: {access_token}")
                print(f"刷新令牌: {refresh_token}")
                print("-" * 50)

                # 更新后端
                car_id = f"ChatGPT-{car_id_counter}"
                backend_response = update_backend(account['email'], account['password'], session_id, car_id)
                print(f"后端更新响应: {backend_response}")
                print("-" * 50)

                car_id_counter += 1

            else:
                print(f"无法获取账户的代码: {account['email']}")

    except Exception as e:
        print(f"错误: {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    main()