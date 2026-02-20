# -*- coding: utf-8 -*-
"""
MediaCrawler 爬虫同步适配器
将异步的 MediaCrawler 爬虫封装为同步接口，供 app.py 使用
"""
import asyncio
import os
from typing import List, Dict, Optional
from playwright.async_api import async_playwright

from xhs_crawler.media_platform.xhs.core import XiaoHongShuCrawler
from xhs_crawler.media_platform.xhs.client import XiaoHongShuClient
from xhs_crawler.media_platform.xhs.exception import CaptchaRequiredError
from xhs_crawler.media_platform.xhs.field import SearchSortType
from xhs_crawler.media_platform.xhs.help import get_search_id
from xhs_crawler.tools import utils
from xhs_crawler.tools.crawler_util import convert_cookies


class XHSCrawlerAdapter:
    """MediaCrawler 爬虫的同步适配器"""
    
    def __init__(self):
        self.base_url = "https://www.xiaohongshu.com"
        self.crawler = None
        self._loop = None
        self._playwright = None  # 保存 playwright 实例，避免自动关闭
        self._browser_context = None
        self._context_page = None
        self._xhs_client = None
        
    def _get_event_loop(self):
        """获取或创建事件循环（兼容 Python 3.10+，同一线程内复用同一 loop）"""
        if self._loop is not None and not self._loop.is_closed():
            return self._loop
        try:
            loop = asyncio.get_running_loop()
            return loop
        except RuntimeError:
            pass
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        return self._loop
    
    def _run_async(self, coro):
        """在同步上下文中运行异步协程（同步封装入口）"""
        loop = self._get_event_loop()
        return loop.run_until_complete(coro)
    
    async def _init_browser_async(self):
        """异步初始化浏览器"""
        if self._browser_context is not None:
            return
        
        self.crawler = XiaoHongShuCrawler()
        
        # 启动 playwright（不使用 async with，保持生命周期）
        if self._playwright is None:
            self._playwright = await async_playwright().start()
        
        chromium = self._playwright.chromium
        
        # 使用持久化上下文保存登录状态
        user_data_dir = os.path.join(os.path.dirname(__file__), 'browser_data', 'xhs_user_data_dir')
        os.makedirs(user_data_dir, exist_ok=True)
        
        try:
            self._browser_context = await chromium.launch_persistent_context(
                user_data_dir=user_data_dir,
                accept_downloads=True,
                headless=False,  # 显示浏览器窗口
                viewport={"width": 1920, "height": 1080},
                user_agent=self.crawler.user_agent,
            )
        except Exception as e:
            error_msg = str(e)
            if "Executable doesn't exist" in error_msg or "playwright" in error_msg.lower():
                print("\n" + "="*60)
                print("[错误] Playwright 浏览器未安装！")
                print("="*60)
                print("\n请运行以下命令安装浏览器：")
                print("  python -m playwright install chromium")
                print("\n或者运行：")
                print("  安装依赖.bat")
                print("="*60 + "\n")
                raise RuntimeError(
                    "Playwright 浏览器未安装。请运行 'python -m playwright install chromium' 或 '安装依赖.bat'"
                ) from e
            raise
        
        # 添加反检测脚本
        try:
            stealth_js_path = os.path.join(os.path.dirname(__file__), 'libs', 'stealth.min.js')
            if os.path.exists(stealth_js_path):
                await self._browser_context.add_init_script(path=stealth_js_path)
        except:
            pass  # 如果没有 stealth.min.js，跳过
        
        self._context_page = await self._browser_context.new_page()
        await self._context_page.goto(self.crawler.index_url)
        
        # 等待页面加载
        await asyncio.sleep(2)
        
        # 创建 API 客户端
        cookie_str, cookie_dict = convert_cookies(await self._browser_context.cookies())
        self._xhs_client = XiaoHongShuClient(
            proxy=None,
            headers={
                "accept": "application/json, text/plain, */*",
                "accept-language": "zh-CN,zh;q=0.9",
                "cache-control": "no-cache",
                "content-type": "application/json;charset=UTF-8",
                "origin": "https://www.xiaohongshu.com",
                "pragma": "no-cache",
                "priority": "u=1, i",
                "referer": "https://www.xiaohongshu.com/",
                "sec-ch-ua": '"Chromium";v="136", "Google Chrome";v="136", "Not.A/Brand";v="99"',
                "sec-ch-ua-mobile": "?0",
                "sec-ch-ua-platform": '"Windows"',
                "sec-fetch-dest": "empty",
                "sec-fetch-mode": "cors",
                "sec-fetch-site": "same-site",
                "user-agent": self.crawler.user_agent,
                "Cookie": cookie_str,
            },
            playwright_page=self._context_page,
            cookie_dict=cookie_dict,
        )
        
        # 检查登录状态；未登录时阻塞等待用户登录，避免直接去搜索导致报错
        if not await self._xhs_client.pong():
            utils.logger.warning("未登录状态，请在浏览器中手动登录小红书账号")
            print("\n" + "="*60)
            print("[提示] 请在打开的浏览器中登录小红书账号（扫码或手机号登录）")
            print("登录完成后，爬虫将自动继续，无需重启")
            print("="*60 + "\n")
            await self._wait_for_login_async(timeout=300)  # 最多等待 5 分钟
    
    async def _wait_for_login_async(self, timeout: int = 300):
        """轮询等待用户在小红书页面完成登录，超时则抛错"""
        import time
        deadline = time.monotonic() + timeout
        check_interval = 2
        while time.monotonic() < deadline:
            await asyncio.sleep(check_interval)
            try:
                await self._xhs_client.update_cookies(self._browser_context)
                if await self._xhs_client.pong():
                    utils.logger.info("检测到已登录，继续执行爬虫")
                    print("\n[成功] 已检测到登录，开始爬取...\n")
                    return
            except Exception as e:
                utils.logger.debug(f"登录检查时出错（可忽略）: {e}")
        raise RuntimeError(
            "等待登录超时（{} 分钟）。请先在小红书页面完成登录，再点击「开始爬取」。".format(timeout // 60)
        )
    
    def init_browser(self):
        """初始化浏览器（同步方法）"""
        self._run_async(self._init_browser_async())
    
    async def _search_notes_async(self, keyword: str, max_notes: int = 100) -> List[Dict]:
        """异步搜索笔记"""
        if self._xhs_client is None:
            await self._init_browser_async()
        
        notes = []
        page = 1
        page_size = 20
        search_id = get_search_id()
        
        while len(notes) < max_notes:
            try:
                notes_res = await self._xhs_client.get_note_by_keyword(
                    keyword=keyword,
                    search_id=search_id,
                    page=page,
                    page_size=page_size,
                    sort=SearchSortType.LATEST,  # 使用最新排序
                )
                
                if not notes_res or not notes_res.get("has_more", False):
                    break
                
                items = notes_res.get("items", [])
                for item in items:
                    if item.get("model_type") in ("rec_query", "hot_query"):
                        continue
                    
                    note_id = item.get("id")
                    if not note_id:
                        continue
                    
                    # 获取笔记详情
                    try:
                        note_detail = await self._xhs_client.get_note_by_id(
                            note_id=note_id,
                            xsec_source=item.get("xsec_source", "pc_search"),
                            xsec_token=item.get("xsec_token", ""),
                        )
                        
                        if note_detail:
                            notes.append({
                                'note_id': note_id,
                                'title': note_detail.get('title', ''),
                                'desc': note_detail.get('desc', ''),
                                'xsec_token': item.get("xsec_token", ""),
                                'xsec_source': item.get("xsec_source", "pc_search"),
                            })
                            
                            if len(notes) >= max_notes:
                                break
                    except CaptchaRequiredError as e:
                        if not getattr(self, "_captcha_warned", False):
                            self._captcha_warned = True
                            utils.logger.warning("检测到需要验证(461/471)，请在已打开的浏览器中完成验证后继续；当前笔记已跳过。")
                            print("\n[提示] 小红书要求验证，请在爬虫浏览器中完成验证/滑块，再继续爬取。\n")
                        utils.logger.warning(f"获取笔记详情失败(验证) {note_id}，已跳过")
                        continue
                    except Exception as e:
                        utils.logger.warning(f"获取笔记详情失败 {note_id}: {e}")
                        continue
                
                page += 1
                await asyncio.sleep(1)  # 延迟避免请求过快
                
            except Exception as e:
                error_msg = str(e)
                # 如果是登录相关错误，提示用户登录
                if "login" in error_msg.lower() or "unauthorized" in error_msg.lower() or "401" in error_msg or "需要登录" in error_msg:
                    utils.logger.error("需要登录才能搜索，请在浏览器中登录小红书账号")
                    raise RuntimeError("需要登录才能搜索，请在浏览器中登录小红书账号")
                utils.logger.error(f"搜索笔记出错: {e}")
                # 如果是第一页就失败，直接退出
                if page == 1:
                    break
                # 否则继续尝试下一页
                page += 1
                await asyncio.sleep(2)
        
        return notes[:max_notes]
    
    def search_notes_by_keyword(self, keyword: str, max_notes: int = 100) -> List[Dict]:
        """搜索关键词，获取最新帖子（同步方法）"""
        return self._run_async(self._search_notes_async(keyword, max_notes))
    
    async def _crawl_note_comments_async(
        self, 
        note_id: str, 
        xsec_token: str = "",
        max_comments: int = 100,
        filter_keywords: List[str] = []
    ) -> List[Dict]:
        """异步抓取笔记评论"""
        if self._xhs_client is None:
            await self._init_browser_async()
        
        comments_data = []
        
        try:
            # 如果没有 xsec_token，尝试从搜索中获取
            if not xsec_token:
                # 这里可以尝试其他方式获取 token，暂时使用空字符串
                pass
            
            # 获取所有评论
            all_comments = await self._xhs_client.get_note_all_comments(
                note_id=note_id,
                xsec_token=xsec_token,
                crawl_interval=1.0,
                callback=None,  # 不使用回调，直接收集结果
                max_count=max_comments,
            )
            
            for comment in all_comments:
                # MediaCrawler 返回的评论结构
                # 尝试多种可能的字段名
                content = (comment.get('content', '') or 
                          comment.get('note_comment', {}).get('content', '') or
                          comment.get('text', '') or
                          '')
                
                # 过滤评论
                if filter_keywords and content:
                    if not any(kw in content for kw in filter_keywords):
                        continue
                
                # 提取用户信息 - 尝试多种可能的字段结构
                user_info = (comment.get('user_info', {}) or 
                           comment.get('user', {}) or 
                           comment.get('author', {}) or
                           {})
                
                user_id = (user_info.get('user_id', '') or 
                          user_info.get('id', '') or
                          user_info.get('userid', '') or
                          comment.get('user_id', '') or
                          '')
                
                if not user_id:
                    continue  # 没有用户ID，跳过这条评论
                
                # 构建评论数据
                comments_data.append({
                    'comment_id': comment.get('id', '') or comment.get('comment_id', ''),
                    'content': content,
                    'user': {
                        'user_id': user_id,
                        'nickname': (user_info.get('nickname', '') or 
                                    user_info.get('name', '') or
                                    user_info.get('nick_name', '') or
                                    ''),
                        'avatar': (user_info.get('image', '') or 
                                  user_info.get('avatar', '') or
                                  user_info.get('avatar_url', '') or
                                  ''),
                        'user_url': f"https://www.xiaohongshu.com/user/profile/{user_id}?xsec_source=pc_note",
                    },
                    'like_count': (comment.get('like_count', 0) or 
                                 comment.get('liked_count', 0) or
                                 comment.get('likeCount', 0) or
                                 0),
                    'time': (comment.get('create_time', 0) or 
                            comment.get('time', 0) or
                            comment.get('createTime', 0) or
                            0),
                })
                
                if len(comments_data) >= max_comments:
                    break
            
        except Exception as e:
            utils.logger.error(f"抓取评论出错 {note_id}: {e}")
        
        return comments_data
    
    def crawl_note_comments(
        self, 
        note_id: str, 
        max_comments: int = 100,
        filter_keywords: List[str] = [],
        xsec_token: str = "",
        xsec_source: str = "pc_search"
    ) -> List[Dict]:
        """抓取帖子的评论（同步方法）"""
        return self._run_async(
            self._crawl_note_comments_async(
                note_id=note_id,
                xsec_token=xsec_token,
                max_comments=max_comments,
                filter_keywords=filter_keywords
            )
        )
    
    def close(self):
        """关闭浏览器"""
        if self._browser_context:
            self._run_async(self._close_async())
    
    async def _close_async(self):
        """异步关闭浏览器"""
        if self._browser_context:
            await self._browser_context.close()
            self._browser_context = None
            self._context_page = None
            self._xhs_client = None
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None
        if self._loop and not self._loop.is_closed():
            self._loop.close()
        self._loop = None
