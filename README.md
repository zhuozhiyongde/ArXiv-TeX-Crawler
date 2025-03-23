# ArXiv-TeX-Crawler

ArXiv-TeX-Crawler 是一个用于从 arXiv.org 下载和提取论文 TeX 源代码的工具，使用 OpenAI API 智能筛选论文核心内容。其输出可以用于后续送入 LLM 进行论文总结、提问等。

## ✨ 功能特点

-   自动下载指定 arXiv ID 的论文源代码压缩包
-   智能解析并提取包含论文核心内容的 TeX 文件
-   使用 OpenAI API 评估 TeX 文件重要性并过滤不重要章节
-   生成包含论文核心内容的单一 TeX 文件

## 🛠️ 配置

在项目根目录创建 `.env` 文件，添加以下内容：

```
OPENAI_API_KEY=你的OpenAI_API密钥
OPENAI_BASE_URL=https://api.openai.com/v1  # 可选，用于自定义API地址
```

## 🚀 使用方法

```bash
# 基本用法
python main.py --arxiv_id "1706.03762"

# 使用URL（会自动提取ID）
python main.py --arxiv_id "https://arxiv.org/abs/1706.03762"
```

输出会保存在根目录。

## 📝 许可证

[MIT License](LICENSE)
