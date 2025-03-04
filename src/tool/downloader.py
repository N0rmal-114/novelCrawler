from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from requests import Session
import time
import os

from src.configs.config import Config
from src.tool.parser import parse_download_url


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
                    save_path = os.path.join(Config.SAVE_PATH, filename)

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