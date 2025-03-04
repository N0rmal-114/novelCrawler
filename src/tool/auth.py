import requests
from requests import Session
import re
import time

from requests.exceptions import RequestException
from src.configs.config import Config


class LoginException(Exception):
    """自定义登录异常"""
    pass


# 单例模式的全局会话对象
_auth_session = None


def create_authenticated_session(max_retry=3) -> Session:
    global _auth_session
    """创建带完整认证流程的会话"""
    if _auth_session is not None:
        return _auth_session

    _auth_session = Session()
    _auth_session.headers.update(Config.HEADERS)

    for attempt in range(max_retry):
        try:
            # 第一步：获取登录页并提取参数
            login_page_url = f"{Config.LOGIN_URL}?jumpurl={requests.utils.quote(Config.BASE_URL)}"
            login_page = _auth_session.get(login_page_url, timeout=10)
            login_page.encoding = 'gbk'

            # 提取隐藏参数（如果有）
            token_match = re.search(r'name="token" value="(.*?)"', login_page.text)
            token = token_match.group(1) if token_match else ''

            # 构造登录数据
            login_data = {
                'username': Config.USERNAME,
                'password': Config.PASSWORD,
                'usecookie': '2592000',
                'action': 'login',
                'submit': '登录',
                'token': token,
                'jumpurl': Config.BASE_URL
            }

            # 第二步：发送登录请求
            response = _auth_session.post(
                f"{Config.LOGIN_URL}?do=submit",
                data=login_data,
                allow_redirects=True,
                timeout=15
            )
            response.encoding = 'gbk'

            # 第三步：验证登录状态
            if 'jieqiUserInfo' not in _auth_session.cookies.get_dict():
                error_msg = extract_error_message(response.text)
                raise LoginException(f"登录失败: {error_msg}")

            print("登录成功！")
            return _auth_session

        except RequestException as e:
            if attempt == max_retry - 1:
                raise LoginException(f"网络请求失败: {str(e)}")
            time.sleep(2 ** attempt)  # 指数退避

    raise LoginException("超过最大重试次数")


def extract_error_message(html: str) -> str:
    """从响应HTML中提取错误信息"""
    error_match = re.search(r'<div class="notice">(.*?)</div>', html, re.DOTALL)
    if error_match:
        return re.sub(r'\s+', ' ', error_match.group(1)).strip()
    return "未知错误"
