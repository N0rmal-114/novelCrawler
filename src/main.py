import os
import logging
from src.configs.config import Config
from src.tool.crawler import Crawler
from src.tool.excel_saver import save_to_excel

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def main():
    try:
        # 创建保存目录
        os.makedirs(Config.SAVE_PATH, exist_ok=True)

        # 初始化爬虫
        crawler = Crawler()

        # 指定爬取页数,如果不指定，默认爬取第一页到最后一页
        novels_data = crawler.crawl_all_pages(start_page=1)
        total_count = len(novels_data)

        # 保存结果
        if novels_data:
            save_to_excel(novels_data, 'novels_list.xlsx')

        # 下载所有小说
        crawler.download_all(novels_data, total_count)

    except Exception as e:
        logging.error(f"程序执行失败: {str(e)}", exc_info=True)

if __name__ == '__main__':
    main()