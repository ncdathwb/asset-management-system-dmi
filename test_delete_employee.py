import requests
from bs4 import BeautifulSoup

BASE_URL = 'http://127.0.0.1:5000'
USERNAME = 'ncdat'
PASSWORD = 'ncdat'
BRANCH = 'vietnam'
EMPLOYEE_ID = 113   # ID nhân viên test

session = requests.Session()

# 1. Lấy CSRF token từ trang login
print("Getting CSRF token...")
login_page = session.get(f'{BASE_URL}/login')
soup = BeautifulSoup(login_page.text, 'html.parser')
csrf_token = soup.find('input', {'name': 'csrf_token'})
if csrf_token:
    csrf_token_value = csrf_token['value']
    print(f"CSRF token found: {csrf_token_value[:10]}...")
else:
    print("CSRF token not found!")
    exit(1)

# 2. Đăng nhập với CSRF token
login_url = f'{BASE_URL}/login'
login_data = {
    'username': USERNAME,
    'password': PASSWORD,
    'branch': BRANCH,
    'csrf_token': csrf_token_value
}
print(f"Attempting login with: {USERNAME}/{PASSWORD} on branch {BRANCH}")
resp = session.post(login_url, data=login_data)
print(f"Login response status: {resp.status_code}")

# Kiểm tra login thành công: status 200 và không chứa error message
if resp.status_code == 200 and 'error' not in resp.text.lower():
    print('Login successful!')
else:
    print('Login failed!')
    print(f"Response preview: {resp.text[:300]}...")
    exit(1)

# 3. Gửi request DELETE để xóa nhân viên
url = f'{BASE_URL}/api/employees/{EMPLOYEE_ID}'
print(f"Sending DELETE request to: {url}")

# Gửi DELETE request với CSRF token
headers = {
    'X-CSRFToken': csrf_token_value,
    'Content-Type': 'application/x-www-form-urlencoded'
}
data = {
    'csrf_token': csrf_token_value
}
resp = session.delete(url, headers=headers, data=data)
print('Status code:', resp.status_code)
print('Response text:', resp.text) 