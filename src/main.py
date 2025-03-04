import requests
from bs4 import BeautifulSoup
import pandas as pd
import re

# 配置信息
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

def parse_novel_info(html_content):
    """解析小说信息"""
    soup = BeautifulSoup(html_content, 'html.parser')
    novels = []

    # 定位所有小说条目
    items = soup.select('div[style="width:373px;height:136px;float:left;margin:5px 0px 5px 5px;"]')

    for item in items:
        try:
            # 基础信息
            title_tag = item.select_one('b a[style="font-size:13px;"]')
            title = title_tag.text.strip()
            detail_url = title_tag['href']

            # 封面图片
            cover_img = item.select_one('img')
            cover_url = cover_img['src'] if cover_img else ''

            # 作者和分类
            author_info = item.select('p')[0].text.strip()
            author = re.search(r'作者:(.*?)/', author_info).group(1).strip()
            category = re.search(r'分类:(.*)', author_info).group(1).strip()

            # 更新信息
            update_info = item.select('p')[1].text.strip()
            update_time = re.search(r'更新:(.*?)/', update_info).group(1).strip()
            word_count = re.search(r'字数:(.*?)/', update_info).group(1).strip() if '字数' in update_info else ''
            status = re.search(r'/([^/]+)$', update_info).group(1).strip()

            # 标签处理
            tags = []
            tags_span = item.select('p span[style*="font-weight:bold;color: #1b74bc;"]')
            if tags_span:
                tags = [tag.strip() for tag in tags_span[0].text.split(' ') if tag.strip()]

            # 简介处理（需要过滤公告信息）
            intro_para = item.find('p', text=re.compile('简介:'))
            if intro_para:
                introduction = intro_para.text.replace('简介:', '').strip()
            else:
                introduction = ''

            novels.append({
                "书名": title,
                "作者": author,
                "分类": category,
                "更新时间": update_time,
                "字数": word_count,
                "状态": status,
                "标签": ", ".join(tags),
                "简介": introduction,
                "封面链接": cover_url,
                "详情页链接": detail_url
            })
        except Exception as e:
            print(f"解析条目失败: {e}")
            continue

    return novels

def save_to_excel(data, filename="novels.xlsx"):
    """保存数据到Excel"""
    df = pd.DataFrame(data)
    # 列顺序调整
    columns = ["书名", "作者", "分类", "更新时间", "字数", "状态", "标签", "简介", "封面链接", "详情页链接"]
    df = df[columns]
    df.to_excel(filename, index=False)
    print(f"数据已保存到 {filename}")

if __name__ == "__main__":
    # 从本地文件读取HTML（假设保存为page.html）
    with open("page.html", "r", encoding="gbk") as f:
        html_content = f.read()

    # 实际使用时可以替换为在线获取
    # url = "https://www.wenku8.net/modules/article/articlelist.php"
    # response = requests.get(url, headers=HEADERS)
    # response.encoding = 'gbk'
    # html_content = response.text

    novels_data = parse_novel_info(html_content)

    if novels_data:
        save_to_excel(novels_data)
    else:
        print("未提取到小说数据")