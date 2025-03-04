import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 基础配置
class Config:
    BASE_URL = 'https://www.wenku8.net/modules/article/articlelist.php?page='
    LOGIN_URL = 'https://www.wenku8.net/login.php'
    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Referer': BASE_URL,
        'Origin': 'https://www.wenku8.net'
    }
    USERNAME = os.getenv('WENKU_USER', 'badboy44')
    PASSWORD = os.getenv('WENKU_PASS', '123leijuikai')
    DELAY = 3
    SAVE_PATH = 'books'
    MIRROR_RETRY_DELAY = 3
    MIRROR_MAX_RETRIES = 2