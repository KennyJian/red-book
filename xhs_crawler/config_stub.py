# -*- coding: utf-8 -*-
"""
配置占位符 - 简化版本的配置对象
用于替代 MediaCrawler 的 config 模块
"""

# 默认配置值
ENABLE_IP_PROXY = False
IP_PROXY_POOL_COUNT = 1
ENABLE_CDP_MODE = False
CDP_HEADLESS = False
HEADLESS = False
LOGIN_TYPE = "qrcode"  # qrcode, phone, cookie
COOKIES = ""
CRAWLER_TYPE = "search"  # search, detail, creator
KEYWORDS = ""
CRAWLER_MAX_NOTES_COUNT = 100
START_PAGE = 1
SORT_TYPE = "time_descending"
MAX_CONCURRENCY_NUM = 3
CRAWLER_MAX_SLEEP_SEC = 1.0
ENABLE_GET_COMMENTS = True
CRAWLER_MAX_COMMENTS_COUNT_SINGLENOTES = 100
ENABLE_GET_SUB_COMMENTS = False
ENABLE_GET_MEIDAS = False
SAVE_LOGIN_STATE = True
USER_DATA_DIR = "%s_user_data_dir"
PLATFORM = "xhs"
