from urllib.parse import urljoin

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
SAVE_PATH = 'books'
MIRROR_RETRY_DELAY = 3  # 镜像重试间隔
MIRROR_MAX_RETRIES = 2  # 单个镜像最大重试次数


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
                '链接': 'https://www.wenku8.net' + title_tag['href'],
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


# def save_to_excel(data: List[Dict], filename: str):
#     """保存数据到Excel"""
#     df = pd.DataFrame(data)
#
#     # 列顺序调整
#     columns = ['标题', '作者', '出版社', '字数', '状态', '最后更新',
#                '标签', '简介', '链接', '封面']
#
#     # 去重处理
#     df = df.drop_duplicates(subset=['标题', '作者'])
#
#     with pd.ExcelWriter(filename, engine='openpyxl') as writer:
#         df.to_excel(writer, index=False, columns=columns)
#
#     print(f"已保存 {len(df)} 条数据到 {filename}")
def save_to_excel(data: List[Dict], filename: str):
    """保存数据到Excel"""
    try:
        df = pd.DataFrame(data)
        columns = ['标题', '作者', '出版社', '字数', '状态', '最后更新', '标签', '简介', '链接', '封面']
        df = df.drop_duplicates(subset=['标题', '作者'])

        # 使用绝对路径
        save_path = os.path.abspath(filename)

        # 检查文件是否被锁定
        if os.path.exists(save_path):
            try:
                os.rename(save_path, save_path)  # 测试文件是否可操作
            except OSError as e:
                print(f"错误：文件 {save_path} 被其他程序占用，请关闭Excel后重试")
                return

        # 修改后的写入代码
        with pd.ExcelWriter(
                save_path,
                engine='openpyxl',
                mode='w'
        ) as writer:
            df.to_excel(writer, index=False, columns=columns)

        print(f"成功保存 {len(df)} 条数据到 {save_path}")

    except PermissionError:
        print(f"权限拒绝：请检查：1. 是否已关闭Excel文件 2. 是否有写权限 3. 尝试管理员模式运行")
    except Exception as e:
        print(f"保存失败：{str(e)}")


def crawl_all_pages(start_page: int = 1, end_page: int = 5):
    """分页抓取小说数据"""
    all_novels = []
    session = create_authenticated_session()

    for page in range(start_page, end_page + 1):
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


# def parse_download_url(html: str) -> str:
#     """解析小说详情页获取TXT下载页面链接"""
#     soup = BeautifulSoup(html, 'html.parser')
#
#
# def download_txt(novel: dict, session: Session, base_url: str = "https://www.wenku8.net"):
#     """在下载页面通过下载链接开始下载"""
def parse_download_url(html: str) -> str:
    """从小说详情页解析TXT全本下载页面链接"""
    soup = BeautifulSoup(html, 'html.parser')

    # 定位TXT全本下载按钮
    download_link = soup.find('a', string='TXT简繁全本')
    if not download_link:
        download_link = soup.find('a', href=lambda x: x and 'type=txtfull' in x)

    if download_link:
        return urljoin("https://www.wenku8.net", download_link['href'])
    raise ValueError("未找到全本下载链接")


# def download_txt(novel: dict, session: Session, base_url: str = "https://www.wenku8.net"):
#     """执行完整下载流程"""
#     try:
#         # 第一步：获取下载页面
#         download_page_url = parse_download_url(novel['html_content'])
#         print(f"正在获取下载页面：{download_page_url}")
#
#         # 第二步：访问下载页面
#         download_page = session.get(download_page_url)
#         download_page.encoding = 'gbk'
#
#         # 第三步：解析下载链接
#         soup = BeautifulSoup(download_page.text, 'html.parser')
#         download_table = soup.find('table', {'class': 'grid'})
#
#         # 定位简体下载链接
#         simplified_links = []
#         for row in download_table.find_all('tr'):
#             if '简体(G)' in row.text:
#                 links = row.find_all('a', href=True)
#                 simplified_links = [urljoin(base_url, l['href']) for l in links if 'type=txt' in l['href']]
#                 break
#
#         if not simplified_links:
#             raise ValueError("未找到简体下载链接")
#
#         # 第四步：下载文件
#         for i, dl_url in enumerate(simplified_links[:2], 1):  # 取前2个镜像
#             print(f"正在下载第{i}个镜像：{dl_url}")
#             response = session.get(dl_url, stream=True)
#
#             # 从URL提取文件名
#             filename = f"{novel['标题']}_简体版_{i}.txt"
#             invalid_chars = ['/', '\\', ':', '*', '?', '"', '<', '>', '|']
#             for char in invalid_chars:
#                 filename = filename.replace(char, '_')
#
#             save_path = os.path.join(SAVE_PATH, filename)
#
#             with open(save_path, 'wb') as f:
#                 for chunk in response.iter_content(chunk_size=8192):
#                     if chunk:
#                         f.write(chunk)
#             print(f"已保存到：{save_path}")
#             time.sleep(DELAY)
#
#     except Exception as e:
#         print(f"下载失败：{str(e)}")

def download_txt(novel: dict, session: Session, base_url: str = "https://www.wenku8.net"):
    """智能下载流程（带镜像重试机制）"""
    try:
        # 获取下载页面
        download_page_url = parse_download_url(novel['html_content'])
        print(f"正在解析下载页面：{download_page_url}")

        # 访问下载页
        download_page = session.get(download_page_url)
        download_page.encoding = 'gbk'

        # 解析下载选项
        soup = BeautifulSoup(download_page.text, 'html.parser')
        download_table = soup.find('table', {'class': 'grid'})

        # 提取所有简体镜像链接
        simplified_links = []
        for row in download_table.find_all('tr'):
            if '简体' in row.text:
                links = [urljoin(base_url, l['href'])
                         for l in row.find_all('a', href=True)
                         if 'type=txt' in l['href']]
                simplified_links.extend(links)
                break

        if not simplified_links:
            raise ValueError("未找到有效下载链接")

        # 智能下载逻辑
        success = False
        for idx, dl_url in enumerate(simplified_links, 1):
            retry_count = 0
            max_retries = 2  # 最大重试次数

            while retry_count <= max_retries and not success:
                try:
                    print(f"尝试镜像{idx}{f' 第{retry_count + 1}次重试' if retry_count > 0 else ''}: {dl_url}")
                    response = session.get(dl_url, stream=True, timeout=20)
                    response.raise_for_status()

                    # 构建安全文件名
                    filename = f"{novel['标题']}_简体版.txt"
                    invalid_chars = {'/', '\\', ':', '*', '?', '"', '<', '>', '|'}
                    filename = ''.join([c if c not in invalid_chars else '_' for c in filename])
                    save_path = os.path.join(SAVE_PATH, filename)

                    # 流式写入文件
                    with open(save_path, 'wb') as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            if chunk:
                                f.write(chunk)

                    print(f"成功保存到：{save_path}")
                    success = True
                    break

                except requests.exceptions.RequestException as e:
                    if retry_count < max_retries:
                        print(f"镜像{idx}下载失败，3秒后重试... 错误：{str(e)}")
                        time.sleep(3)
                        retry_count += 1
                    else:
                        print(f"镜像{idx}超过最大重试次数，切换下一个镜像")
                        break  # 跳出重试循环，切换镜像

                except IOError as e:
                    print(f"文件写入失败：{str(e)}")
                    break  # 文件系统错误直接终止

            if success:
                break  # 成功则终止镜像循环

        if not success:
            raise Exception("所有镜像均不可用")

    except Exception as e:
        print(f"下载流程失败：{str(e)}")
        raise


def download_all(novels: list[dict], total_count: int):
    # 初始化统计指标
    start_time = time.time()
    total_count = total_count
    success_count = 0
    fail_count = 0
    total_size = 0  # 单位：字节
    # 下载处理循环

    for idx, novel in enumerate(novels, 1):
        novel_title = novel['标题']
        print(f"\n[{idx}/{total_count}] 正在处理：{novel_title}")

        try:
            # 获取详情页
            novel['html_content'] = get_html(novel['链接'], auth_session)

            # 执行下载
            start_dl = time.time()
            download_txt(novel, auth_session)

            # 计算文件大小
            filename = f"{novel_title}_简体版.txt".translate(str.maketrans('', '', r'\/:*?"<>|'))
            file_path = os.path.join(SAVE_PATH, filename)
            if os.path.exists(file_path):
                file_size = os.path.getsize(file_path)
                total_size += file_size
                print(f"文件大小：{file_size / 1024:.2f} KB")

            success_count += 1
            time.sleep(2)

        except Exception as e:
            fail_count += 1
            print(f"❗{novel_title} 处理失败：{str(e)}")
            continue
            # 统计结果输出
    end_time = time.time()
    time_cost = end_time - start_time
    print("\n" + "=" * 40)
    print("📊 任务统计报告")
    print("-" * 40)
    print(f"总处理数量：{total_count}")
    print(f"✅ 成功数量：{success_count} ({success_count / total_count:.1%})")
    print(f"❌ 失败数量：{fail_count} ({fail_count / total_count:.1%})")
    print(f"⏱️ 总耗时：{time_cost // 3600:.0f}小时{time_cost % 3600 // 60:.0f}分{time_cost % 60:.2f}秒")
    print(f"📦 总下载量：{total_size / 1024 / 1024:.2f} MB")
    print("=" * 40)


if __name__ == '__main__':

    # 初始化全局会话
    auth_session = create_authenticated_session()
    os.makedirs(SAVE_PATH, exist_ok=True)

    # 抓取前2页数据
    novels_data = crawl_all_pages(start_page=1, end_page=2)
    total_count = len(novels_data)

    # 保存结果
    if novels_data:
        save_to_excel(novels_data, 'novels_list.xlsx')

    download_all(novels_data, total_count)

# if __name__ == '__main__':
#     # 初始化全局会话
#     auth_session = create_authenticated_session()
#
#     # 测试访问
#     # test_url = f"{BASE_URL}1"
#     # html_content = get_html(test_url, auth_session)
#
#     # 抓取前5页数据
#     novels_data = crawl_all_pages(start_page=1, end_page=2)
#
#     #从novels_data中访问每个小说的链接并从中下载TXT
#     for novel in novels_data:
#         novel_url = novel['链接']
#         html_content = get_html(novel_url, auth_session)
#         parse_download_url(html_content)
#
#
#     # 保存结果
#     if novels_data:
#         save_to_excel(novels_data, 'novels_list.xlsx')
# print(html_content)
# if html_content:
#     with open('output.html', 'w', encoding='gbk') as f:
#         f.write(html_content)
#     print("页面已保存至output.html")
