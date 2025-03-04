from urllib.parse import urljoin

from bs4 import BeautifulSoup
from typing import List, Dict

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