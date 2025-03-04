from typing import List, Dict

import pandas as pd
import os

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