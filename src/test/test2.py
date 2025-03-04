import requests
from requests import Session
import re
import os
from dotenv import load_dotenv
import time
import pandas as pd
from bs4 import BeautifulSoup
from typing import List, Dict

# 加载环境变量
load_dotenv()

# 基础配置
BASE_URL = 'https://www.wenku8.net/modules/article/articlelist.php?page='
LOGIN_URL = 'https://www.wenku8.net/login.php'
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Referer': BASE_URL,
    'Origin': 'https://www.wenku8.net'
}

# 环境变量配置
USERNAME = os.getenv('WENKU_USER', 'badboy44')  # 优先从环境变量读取
PASSWORD = os.getenv('WENKU_PASS', '123leijuikai')
DELAY = 3

class LoginException(Exception):
    """自定义登录异常"""
    pass


def create_authenticated_session(max_retry=3) -> Session:
    """创建带完整认证流程的会话"""
    session = Session()
    session.headers.update(HEADERS)

    for attempt in range(max_retry):
        try:
            # 第一步：获取登录页并提取参数
            login_page_url = f"{LOGIN_URL}?jumpurl={requests.utils.quote(BASE_URL)}"
            login_page = session.get(login_page_url, timeout=10)
            login_page.encoding = 'gbk'

            # 提取隐藏参数（如果有）
            token_match = re.search(r'name="token" value="(.*?)"', login_page.text)
            token = token_match.group(1) if token_match else ''

            # 构造登录数据
            login_data = {
                'username': USERNAME,
                'password': PASSWORD,
                'usecookie': '2592000',
                'action': 'login',
                'submit': '登录',
                'token': token,
                'jumpurl': BASE_URL
            }

            # 第二步：发送登录请求
            response = session.post(
                f"{LOGIN_URL}?do=submit",
                data=login_data,
                allow_redirects=True,
                timeout=15
            )
            response.encoding = 'gbk'

            # 第三步：验证登录状态
            if 'jieqiUserInfo' not in session.cookies.get_dict():
                error_msg = extract_error_message(response.text)
                raise LoginException(f"登录失败: {error_msg}")

            print("登录成功！")
            return session

        except requests.exceptions.RequestException as e:
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


def get_html(url: str, session: Session = None) -> str:
    """获取网页内容"""
    try:
        # 复用会话或创建新会话
        if not session or not isinstance(session, Session):
            session = create_authenticated_session()

        print(f"正在访问 {url}")
        response = session.get(url, timeout=15)
        response.encoding = 'gbk'

        # 检查是否被登出
        if '请先登录' in response.text:
            raise LoginException("会话已过期，需要重新登录")

        return response.text

    except Exception as e:
        print(f"请求失败: {str(e)}")
        return None

def parse_novel_list(html: str) -> List[Dict]:
    """解析小说列表页面"""
    soup = BeautifulSoup(html, 'html.parser')
    novels = []

    # 定位小说项容器
    items = soup.select('div[style*="width:373px;height:136px;float:left"]')

    for item in items:
        try:
            # 提取基本信息
            title_tag = item.select_one('b > a[title]')
            detail_div = item.select_one('div:not([style*="width:95px"])')

            # 基础信息
            novel = {
                '标题': title_tag.get_text(strip=True),
                '链接': title_tag['href'],
                '封面': item.select_one('img')['src'],
                '作者': detail_div.select('p')[0].get_text().split(':')[-1].split('/')[0].strip(),
                '出版社': detail_div.select('p')[0].get_text().split('/')[-1].split(':')[-1].strip(),
                '最后更新': detail_div.select('p')[1].get_text().split('/')[0].split(':')[-1].strip(),
                '字数': detail_div.select('p')[1].get_text().split('/')[1].strip(),
                '状态': detail_div.select('p')[1].get_text().split('/')[-1].strip(),
                '标签': detail_div.select('p')[2].get_text(strip=True).replace('Tags:', ''),
                '简介': detail_div.select('p')[3].get_text(strip=True)
            }

            # 处理特殊状态标记
            if 'hottext' in detail_div.select('p')[1].get_text():
                novel['状态'] = '已完结'

            novels.append(novel)
        except Exception as e:
            print(f"解析小说条目失败: {str(e)}")
            continue

    return novels

def save_to_excel(data: List[Dict], filename: str):
    """保存数据到Excel"""
    df = pd.DataFrame(data)

    # 列顺序调整
    columns = ['标题', '作者', '出版社', '字数', '状态', '最后更新',
               '标签', '简介', '链接', '封面']

    # 去重处理
    df = df.drop_duplicates(subset=['标题', '作者'])

    with pd.ExcelWriter(filename, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, columns=columns)

    print(f"已保存 {len(df)} 条数据到 {filename}")

def crawl_all_pages(start_page: int = 1, end_page: int = 5):
    """分页抓取小说数据"""
    all_novels = []
    session = create_authenticated_session()

    for page in range(start_page, end_page+1):
        try:
            url = f"{BASE_URL}{page}"
            html = get_html(url, session)

            if html:
                novels = parse_novel_list(html)
                all_novels.extend(novels)
                print(f"第 {page} 页抓取完成，累计 {len(all_novels)} 条数据")

                # 遵守爬取间隔
                time.sleep(DELAY)

        except Exception as e:
            print(f"第 {page} 页抓取失败: {str(e)}")
            continue

    return all_novels


if __name__ == '__main__':
    # 初始化全局会话
    auth_session = create_authenticated_session()

    # 测试访问
    test_url = f"{BASE_URL}1"
    html_content = get_html(test_url, auth_session)
    # print(html_content)
    # if html_content:
    #     with open('output.html', 'w', encoding='gbk') as f:
    #         f.write(html_content)
    #     print("页面已保存至output.html")
