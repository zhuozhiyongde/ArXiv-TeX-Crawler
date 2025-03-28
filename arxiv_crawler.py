#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# @Author  :   Arthals
# @File    :   arxiv_crawler.py
# @Time    :   2025/03/23 17:16:19
# @Contact :   zhuozhiyongde@126.com
# @Software:   Cursor


import os
import re
import tarfile
from pathlib import Path

import pyperclip
import requests
from openai import OpenAI


class ArXivCrawler:
    def __init__(self, api_key=None, theta=0.7):
        self.base_url = "https://arxiv.org/src/"
        self.tex_files = []
        self.output_content = []
        self.theta = theta  # 置信度阈值
        self.use_llm = True  # 默认使用 LLM
        # 设置OpenAI API密钥
        if api_key:
            self.client = OpenAI(api_key=api_key)
        else:
            self.client = OpenAI(
                api_key=os.environ.get("OPENAI_API_KEY"),
                base_url=os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1"),
            )

    def _evaluate_tex_content(self, content):
        """使用OpenAI模型评估TeX内容的重要性"""
        try:
            prompt = """判断这段LaTeX内容是否包含：摘要、相关工作、方法、讨论等章节内容，而不是实验、附录等。
            请仅输出一个0到1之间的置信度值，表示该内容对理解论文核心有多重要。
            
            内容:
            """

            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": "你是一个学术论文分析助手，只输出一个0到1之间的数字表示置信度。",
                    },
                    {
                        "role": "user",
                        "content": prompt + content[:4000],
                    },  # 限制内容长度
                ],
                temperature=0.3,
                max_tokens=10,
            )

            score_text = response.choices[0].message.content.strip()
            # 尝试从响应中提取数字
            try:
                score = float(re.search(r"0\.\d+|\d+", score_text).group())
                return min(max(score, 0), 1)  # 确保在0-1范围内
            except (ValueError, AttributeError):
                print(f"无法解析模型输出: {score_text}，默认返回0.5")
                return 0.5

        except Exception as e:
            print(f"评估内容时出错: {str(e)}")
            return 0  # 出错时返回0

    def _download_archive(self, arxiv_id):
        """下载arxiv源码压缩包，支持自动补全文件名后缀"""
        # 检查本地是否已存在数据目录
        data_dir = Path("data") / arxiv_id
        if data_dir.exists() and any(data_dir.rglob("*.tex")):
            print(f"发现本地已存在 {arxiv_id} 的源码，直接使用")
            self.tex_files = list(data_dir.rglob("*.tex"))
            return None, None

        # 询问是否使用 LLM 筛选
        if input("是否使用 LLM 进行相关度筛选？(回车确认，输入任意字符取消): ").strip():
            self.use_llm = False
            print("将不使用 LLM 筛选，保留所有内容")

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
        # 筛选后的tex文件
        filtered_tex_files = []

        # 1. 已经在_extract_tex中只获取了.tex文件

        # 2. 使用OpenAI模型评估每个tex文件
        for tex_file in self.tex_files:
            try:
                with open(tex_file, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()

                if self.use_llm:
                    # 评估该文件内容
                    confidence = self._evaluate_tex_content(content)
                    print(f"文件 {tex_file.name} 的置信度: {confidence}")

                    # 3. 根据置信度决定是否保留
                    if confidence >= self.theta:
                        filtered_tex_files.append((tex_file, content))
                        print(f"保留文件: {tex_file.name}")
                    else:
                        print(f"移除文件: {tex_file.name}")
                else:
                    filtered_tex_files.append((tex_file, content))
                    print(f"保留文件: {tex_file.name}")

            except Exception as e:
                print(f"处理文件 {tex_file} 时出错: {str(e)}")

        # 4. 按文件系统顺序合并内容
        self.output_content = []
        self.output_seq = [tex_file.name for tex_file in self.tex_files]

        if self.use_llm:
            # 使用 OpenAI 模型对输出顺序进行排序
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": "你是学术论文章节排序助手，请根据论文的逻辑顺序，对以下章节进行排序。",
                    },
                    {
                        "role": "user",
                        "content": str(self.output_seq)
                        + "\n请仅输出最终的排序结果，不要输出任何解释。",
                    },
                ],
            )
            seq_str = response.choices[0].message.content.strip()
            print("排序结果: ", seq_str)
            # 根据 tex_file.name 在 seq_str 中的顺序，对 filtered_tex_files 进行排序
            for tex_file, content in sorted(
                filtered_tex_files, key=lambda x: seq_str.index(x[0].name)
            ):
                print("当前文件: ", tex_file.name)
                self.output_content.append(f"% 源文件: {tex_file.name}\n")
                self.output_content.append(content)
        else:
            # 如果不使用 LLM，按文件名排序
            for tex_file, content in sorted(
                filtered_tex_files, key=lambda x: x[0].name
            ):
                print("当前文件: ", tex_file.name)
                self.output_content.append(f"% 源文件: {tex_file.name}\n")
                self.output_content.append(content)

        # 如果没有找到有价值的内容，抛出异常
        if not self.output_content:
            raise ValueError("未找到有价值的TeX内容")

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
