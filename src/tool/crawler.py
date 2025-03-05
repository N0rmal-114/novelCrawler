import os
import time
import logging

from tenacity import sleep

from src.configs.config import Config
from src.tool.auth import create_authenticated_session
from src.tool.html_fetcher import get_html
from src.tool.parser import parse_novel_list
from src.tool.downloader import download_txt

class Crawler:
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)

    def crawl_all_pages(self, start_page: int = 1, end_page: int = None):
        """分页抓取小说数据"""
        all_novels = []
        page = start_page

        while True:
            try:
                url = f"{Config.BASE_URL}{page}"
                self.logger.info(f"正在抓取第 {page} 页")
                html = get_html(url)

                if html:
                    novels = parse_novel_list(html)
                    if not novels:  # 如果当前页没有数据，说明已经爬取完所有页
                        break
                    all_novels.extend(novels)
                    self.logger.info(f"第 {page} 页抓取完成，累计 {len(all_novels)} 条数据")
                    time.sleep(Config.DELAY)
                    page += 1

                    if end_page and page > end_page:  # 如果指定了结束页，则停止爬取
                        break

            except Exception as e:
                self.logger.error(f"第 {page} 页抓取失败: {str(e)}", exc_info=True)
                continue

        return all_novels

    def download_all(self, novels: list[dict], total_count: int):
        """下载所有小说"""
        start_time = time.time()
        success_count = 0
        fail_count = 0
        total_size = 0

        # 创建会话
        session = create_authenticated_session()

        for idx, novel in enumerate(novels, 1):
            novel_title = novel['标题']
            self.logger.info(f"[{idx}/{total_count}] 正在处理：{novel_title}")

            try:
                novel['html_content'] = get_html(novel['链接'], session)
                # 检查 html_content 是否为空
                if not novel['html_content']:
                    self.logger.warning(f"小说详情页内容为空，跳过下载：{novel_title}")
                    continue

                # 判断是否已下载过,如果文件夹中含有文件则跳过
                if os.path.exists(os.path.join(Config.SAVE_PATH, f"{novel_title}_简体版.txt")):
                    self.logger.info(f"文件已存在，跳过下载：{novel_title}")
                    sleep(1)
                    continue
                download_txt(novel, session)

                # 计算文件大小
                filename = f"{novel_title}_简体版.txt".translate(str.maketrans('', '', r'\/:*?"<>|'))
                file_path = os.path.join(Config.SAVE_PATH, filename)
                if os.path.exists(file_path):
                    file_size = os.path.getsize(file_path)
                    total_size += file_size
                    self.logger.info(f"文件大小：{file_size / 1024:.2f} KB")


                success_count += 1
                time.sleep(2)

            except Exception as e:
                fail_count += 1
                self.logger.error(f"❗{novel_title} 处理失败：{str(e)}", exc_info=True)
                continue

        # 输出统计报告
        time_cost = time.time() - start_time
        self.logger.info("\n" + "=" * 40)
        self.logger.info("📊 任务统计报告")
        self.logger.info("-" * 40)
        self.logger.info(f"总处理数量：{total_count}")
        self.logger.info(f"✅ 成功数量：{success_count} ({success_count / total_count:.1%})")
        self.logger.info(f"❌ 失败数量：{fail_count} ({fail_count / total_count:.1%})")
        self.logger.info(f"⏱️ 总耗时：{time_cost // 3600:.0f}小时{time_cost % 3600 // 60:.0f}分{time_cost % 60:.2f}秒")
        self.logger.info(f"📦 总下载量：{total_size / 1024 / 1024:.2f} MB")
        self.logger.info("=" * 40)
