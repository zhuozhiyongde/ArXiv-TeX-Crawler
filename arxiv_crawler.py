#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# @Author  :   Arthals
# @File    :   arxiv_crawler.py
# @Time    :   2025/03/23 17:16:19
# @Contact :   zhuozhiyongde@126.com
# @Software:   Cursor


import os
import tarfile
from pathlib import Path
import pyperclip
import requests


class ArXivCrawler:
    def __init__(self):
        self.base_url = "https://arxiv.org/src/"
        self.tex_files = []
        self.output_content = []

    def _download_archive(self, arxiv_id):
        """下载arxiv源码压缩包，支持自动补全文件名后缀"""
        # 检查本地是否已存在数据目录
        data_dir = Path("data") / arxiv_id
        if data_dir.exists() and any(data_dir.rglob("*.tex")):
            print(f"发现本地已存在 {arxiv_id} 的源码，直接使用")
            self.tex_files = list(data_dir.rglob("*.tex"))
            return None, None

        # 如果本地不存在，则下载
        url = f"https://arxiv.org/src/{arxiv_id}"
        print(f"正在下载: {url}")

        response = requests.get(url, stream=True, timeout=30)
        if response.status_code != 200:
            raise ValueError(f"下载失败，HTTP状态码: {response.status_code}")

        # 自动检测并添加文件后缀
        content_type = response.headers.get("Content-Type", "")
        if "gzip" in content_type or response.url.endswith(".tar.gz"):
            return response.content, "tar.gz"

        return response.content, None

    def _extract_tex(self, archive_data, file_ext, arxiv_id):
        # 如果已经存在本地文件，直接返回
        if archive_data is None and file_ext is None:
            return

        # 创建特定arxiv_id的数据存储目录
        data_dir = Path("data") / arxiv_id
        data_dir.mkdir(parents=True, exist_ok=True)

        # 生成带后缀的文件名
        suffix = f".{file_ext}" if file_ext else ""
        archive_path = data_dir / f"source{suffix}"

        with open(archive_path, "wb") as f:
            f.write(archive_data)

        # 自动检测压缩格式
        if file_ext == "tar.gz" or archive_path.suffix in (".tar.gz", ".tgz"):
            with tarfile.open(archive_path, "r:gz") as tar:
                tar.extractall(path=data_dir)
        else:
            # 尝试自动解压其他格式
            try:
                with tarfile.open(archive_path, "r:*") as tar:
                    tar.extractall(path=data_dir)
            except tarfile.ReadError as e:
                raise ValueError(f"不支持的压缩格式: {e}")

        # 在数据目录中查找所有tex文件
        self.tex_files = list(data_dir.rglob("*.tex"))
        if not self.tex_files:
            raise ValueError("未找到TeX文件")

    def _parse_content(self, arxiv_id):
        # 按文件名排序处理所有tex文件
        self.output_content = []
        for tex_file in sorted(self.tex_files, key=lambda x: x.name):
            try:
                with open(tex_file, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                print(f"处理文件: {tex_file.name}")
                self.output_content.append(f"% 源文件: {tex_file.name}\n")
                self.output_content.append(content)
            except Exception as e:
                print(f"处理文件 {tex_file} 时出错: {str(e)}")

        # 如果没有找到内容，抛出异常
        if not self.output_content:
            raise ValueError("未找到TeX内容")

    def process(self, arxiv_id):
        try:
            archive_data, file_ext = self._download_archive(arxiv_id)
            self._extract_tex(archive_data, file_ext, arxiv_id)
            self._parse_content(arxiv_id)

            if not self.output_content:
                raise ValueError("未找到内容")

            # 保存到根目录
            output_path = f"{arxiv_id}.tex"
            with open(output_path, "w", encoding="utf-8") as f:
                if os.environ.get("CUSTOM_END_PROMPT", None):
                    self.output_content.append(os.environ.get("CUSTOM_END_PROMPT"))
                f.writelines(self.output_content)

            # 复制到剪贴板
            pyperclip.copy("\n".join(self.output_content))

            return output_path

        except Exception as e:
            print(f"处理失败: {str(e)}")
            return None
