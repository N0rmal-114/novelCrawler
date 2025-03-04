import requests
from bs4 import BeautifulSoup
import time
import os

# 配置信息
# BASE_URL = 'https://www.wenku8.net'
BASE_URL = 'https://www.wenku8.net/modules/article/articlelist.php?page='
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Referer': BASE_URL
}
DELAY = 3  # 访问间隔设置为3秒
SAVE_PATH = './novels/'

def get_novel_links():
    """获取所有小说列表页的链接"""
    novel_links = []
    page = 1
    while True:
        url = f"{BASE_URL}/modules/article/articlelist.php?page={page}"
        try:
            res = requests.get(url, headers=HEADERS)
            res.encoding = 'gbk'  # 网站使用gbk编码
            soup = BeautifulSoup(res.text, 'html.parser')

            # 定位小说条目
            items = soup.select('#content table a[href^="/book/"]')
            if not items:
                break

            # 去重处理
            seen = set()
            for a in items:
                if a['href'] not in seen:
                    novel_links.append((a.text.strip(), BASE_URL + a['href']))
                    seen.add(a['href'])

            # 检查是否有下一页
            next_page = soup.select_one('a:contains("下一页")')
            if not next_page:
                break

            page += 1
            time.sleep(DELAY)
        except Exception as e:
            print(f"获取列表页失败: {e}")
            break
    return novel_links

def get_chapters(novel_url):
    """获取单本小说的章节列表"""
    try:
        res = requests.get(novel_url, headers=HEADERS)
        res.encoding = 'gbk'
        soup = BeautifulSoup(res.text, 'html.parser')

        # 定位章节列表
        volume_list = []
        for div in soup.select('#content > div'):
            if '卷' in div.text:
                volume = div.text.strip()
                chapters = []
                for a in div.find_next('div').select('a'):
                    chapters.append((a.text.strip(), BASE_URL + a['href']))
                volume_list.append((volume, chapters))
        return volume_list
    except Exception as e:
        print(f"获取章节失败: {e}")
        return []

def download_chapter(url):
    """下载单个章节内容"""
    try:
        res = requests.get(url, headers=HEADERS)
        res.encoding = 'gbk'
        soup = BeautifulSoup(res.text, 'html.parser')

        title = soup.select_one('#title').text.strip()
        content = soup.select_one('#content').text.strip()
        return title, content
    except Exception as e:
        print(f"下载章节失败: {e}")
        return None, None

def save_novel(title, volumes):
    """按卷保存小说"""
    if not os.path.exists(SAVE_PATH):
        os.makedirs(SAVE_PATH)

    filename = f"{SAVE_PATH}{title}.txt"
    with open(filename, 'w', encoding='utf-8') as f:
        for volume_name, chapters in volumes:
            f.write(f"\n\n=== {volume_name} ===\n\n")
            for chap_title, content in chapters:
                f.write(f"【{chap_title}】\n{content}\n\n")
    print(f"已保存：{filename}")

def main():
    novels = get_novel_links()
    print(f"发现{len(novels)}部小说")

    # for novel_title, novel_url in novels[:1]:  # 测试时限制为1本
    #     print(f"\n开始下载《{novel_title}》")
    #     volumes = get_chapters(novel_url)
    #
    #     all_contents = []
    #     for volume_name, chapters in volumes:
    #         print(f"\n正在下载 {volume_name}")
    #         volume_content = []
    #         for chap_title, chap_url in chapters[:2]:  # 测试时每卷限制2章
    #             print(f"下载章节：{chap_title}")
    #             title, content = download_chapter(chap_url)
    #             if content:
    #                 volume_content.append((title, content))
    #             time.sleep(DELAY)
    #         all_contents.append((volume_name, volume_content))
    #
    #     if all_contents:
    #         save_novel(novel_title, all_contents)

if __name__ == "__main__":
    main()