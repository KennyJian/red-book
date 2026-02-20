# MediaCrawler 小红书爬虫模块

本模块是从 MediaCrawler 项目复制的小红书爬虫代码，已适配到当前项目使用。

## 目录结构

```
xhs_crawler/
├── base/              # 基础抽象类
│   └── base_crawler.py
├── model/             # 数据模型
│   └── m_xiaohongshu.py
├── tools/             # 工具函数
│   ├── crawler_util.py
│   └── utils.py
└── media_platform/
    └── xhs/           # 小红书爬虫核心代码
        ├── core.py           # 爬虫核心类
        ├── client.py          # API 客户端
        ├── login.py           # 登录模块
        ├── extractor.py       # 数据提取器
        ├── field.py           # 字段定义
        ├── exception.py       # 异常定义
        ├── help.py            # 辅助函数
        ├── xhs_sign.py        # 签名算法
        └── playwright_sign.py  # Playwright 签名
```

## 使用方法

### 基本使用

```python
from xhs_crawler.media_platform.xhs import XiaoHongShuCrawler

# 创建爬虫实例
crawler = XiaoHongShuCrawler()

# 启动爬虫（异步）
await crawler.start()
```

### 搜索笔记

```python
# 在 core.py 的 search 方法中已经实现
# 需要配置关键词等参数
```

## 注意事项

1. 本模块是简化版本，移除了部分 MediaCrawler 的依赖（如代理池、缓存等）
2. 需要安装必要的依赖包（见 requirements.txt）
3. 使用前需要先登录小红书账号
4. 请遵守目标平台的使用条款，合理控制爬取频率

## 依赖说明

主要依赖：
- playwright: 浏览器自动化
- httpx: HTTP 客户端
- tenacity: 重试机制
- pydantic: 数据验证
- Pillow: 图片处理
- pyhumps: 驼峰命名转换

## 许可证

本代码来自 MediaCrawler 项目，遵循原项目的许可证条款。
