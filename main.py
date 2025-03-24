#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# @Author  :   Arthals
# @File    :   main.py
# @Time    :   2025/03/23 17:16:26
# @Contact :   zhuozhiyongde@126.com
# @Software:   Cursor


import argparse

from dotenv import load_dotenv

from arxiv_crawler import ArXivCrawler

load_dotenv()


def main():
    parser = argparse.ArgumentParser(description="ArXiv TeX Crawler Test")
    parser.add_argument(
        "--id",
        type=str,
        default="1706.03762",
        help="arXiv article ID (e.g. 1706.03762)",
    )
    args = parser.parse_args()

    if "http" in args.id:
        args.id = args.id.split("/")[-1]

    print(f"正在处理 arXiv ID: {args.id}")
    crawler = ArXivCrawler()

    try:
        result = crawler.process(args.id)
        if result:
            print(f"成功生成文件: {result}")
            # print("文件内容结构验证：")
            # with open(result, "r") as f:
            #     print(f"前10行预览：\n{''.join(f.readlines()[:10])}")
        else:
            print("处理完成但未生成有效文件")
    except Exception as e:
        print(f"处理过程中发生错误: {str(e)}")
        print("可能原因：")
        print("1. arXiv ID 无效或不存在")
        print("2. 压缩包内未找到TeX文件")
        print("3. 文档结构不符合预期")


if __name__ == "__main__":
    main()
