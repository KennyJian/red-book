# -*- coding: utf-8 -*-
"""
小红书爬虫测试脚本
用于测试爬虫核心功能是否正常
"""
import asyncio
import os
from xhs_crawler.media_platform.xhs.core import XiaoHongShuCrawler
from xhs_crawler.media_platform.xhs.field import SearchSortType
from playwright.async_api import async_playwright

async def test_crawler():
    """测试爬虫基本功能"""
    print("=" * 60)
    print("小红书爬虫测试脚本")
    print("=" * 60)
    
    # 创建爬虫实例
    crawler = XiaoHongShuCrawler()
    print(f"\n1. 创建爬虫实例成功")
    print(f"   - 首页URL: {crawler.index_url}")
    print(f"   - User-Agent: {crawler.user_agent[:50]}...")
    
    # 启动Playwright
    print("\n2. 启动浏览器...")
    async with async_playwright() as playwright:
        chromium = playwright.chromium
        
        # 使用持久化浏览器上下文
        user_data_dir = os.path.join(os.getcwd(), "browser_data", "xhs_test")
        os.makedirs(user_data_dir, exist_ok=True)
        
        browser_context = await chromium.launch_persistent_context(
            user_data_dir=user_data_dir,
            accept_downloads=True,
            headless=False,  # 显示浏览器,方便观察
            viewport={"width": 1920, "height": 1080},
            user_agent=crawler.user_agent,
        )
        
        # 添加反检测脚本
        stealth_js_path = os.path.join(os.getcwd(), "libs", "stealth.min.js")
        if os.path.exists(stealth_js_path):
            await browser_context.add_init_script(path=stealth_js_path)
            print("   ✓ 已加载反检测脚本")
        else:
            print("   ⚠ 未找到stealth.min.js,跳过反检测")
        
        # 创建页面
        page = await browser_context.new_page()
        print("   ✓ 浏览器启动成功")
        
        # 访问小红书
        print("\n3. 访问小红书主页...")
        await page.goto(crawler.index_url)
        await page.wait_for_load_state("networkidle")
        print("   ✓ 页面加载完成")
        
        # 创建客户端
        print("\n4. 创建API客户端...")
        cookie_str, cookie_dict = "", {}
        try:
            cookies = await browser_context.cookies()
            cookie_list = []
            for cookie in cookies:
                cookie_list.append(f"{cookie['name']}={cookie['value']}")
                cookie_dict[cookie['name']] = cookie['value']
            cookie_str = "; ".join(cookie_list)
            print(f"   ✓ 获取到 {len(cookie_dict)} 个Cookie")
        except Exception as e:
            print(f"   ⚠ Cookie获取失败: {e}")
        
        from xhs_crawler.media_platform.xhs.client import XiaoHongShuClient
        
        client = XiaoHongShuClient(
            headers={
                "accept": "application/json, text/plain, */*",
                "accept-language": "zh-CN,zh;q=0.9",
                "content-type": "application/json;charset=UTF-8",
                "origin": "https://www.xiaohongshu.com",
                "referer": "https://www.xiaohongshu.com/",
                "user-agent": crawler.user_agent,
                "Cookie": cookie_str,
            },
            playwright_page=page,
            cookie_dict=cookie_dict,
        )
        print("   ✓ API客户端创建成功")
        
        # 检查登录状态
        print("\n5. 检查登录状态...")
        is_logged_in = await client.pong()
        
        if not is_logged_in:
            print("   ⚠ 未登录,需要先登录")
            print("\n请按以下步骤操作:")
            print("1. 在打开的浏览器窗口中点击登录按钮")
            print("2. 使用小红书App扫描二维码登录")
            print("3. 登录成功后按Enter继续测试...")
            input()
            
            # 重新检查登录状态
            await client.update_cookies(browser_context)
            is_logged_in = await client.pong()
            if not is_logged_in:
                print("   ✗ 登录失败,无法继续测试")
                return
        
        print("   ✓ 登录状态正常")
        
        # 测试搜索功能
        print("\n6. 测试搜索功能...")
        print("   搜索关键词: Python")
        
        try:
            from xhs_crawler.media_platform.xhs.help import get_search_id
            
            results = await client.get_note_by_keyword(
                keyword="Python",
                search_id=get_search_id(),
                page=1,
                page_size=5,
                sort=SearchSortType.LATEST
            )
            
            items = results.get("items", [])
            print(f"   ✓ 搜索成功,找到 {len(items)} 条笔记")
            
            # 显示前3条结果
            for i, item in enumerate(items[:3], 1):
                note_id = item.get("id", "未知")
                # 注意: 搜索结果的数据结构可能不同,需要根据实际调整
                print(f"     {i}. 笔记ID: {note_id}")
            
            # 测试获取笔记详情
            if items:
                print("\n7. 测试获取笔记详情...")
                first_note = items[0]
                note_id = first_note.get("id")
                xsec_token = first_note.get("xsec_token", "")
                xsec_source = first_note.get("xsec_source", "pc_search")
                
                print(f"   获取笔记ID: {note_id}")
                
                try:
                    note_detail = await client.get_note_by_id(
                        note_id=note_id,
                        xsec_source=xsec_source,
                        xsec_token=xsec_token
                    )
                    
                    if note_detail:
                        title = note_detail.get("title", "无标题")
                        user_info = note_detail.get("user", {})
                        nickname = user_info.get("nickname", "未知")
                        
                        print(f"   ✓ 获取成功")
                        print(f"     标题: {title}")
                        print(f"     作者: {nickname}")
                    else:
                        print("   ⚠ 笔记详情为空")
                        # 尝试从HTML获取
                        print("   尝试从HTML获取...")
                        note_detail = await client.get_note_by_id_from_html(
                            note_id=note_id,
                            xsec_source=xsec_source,
                            xsec_token=xsec_token,
                            enable_cookie=True
                        )
                        if note_detail:
                            print("   ✓ 从HTML获取成功")
                        else:
                            print("   ✗ HTML获取也失败")
                    
                    # 测试获取评论
                    if xsec_token:
                        print("\n8. 测试获取评论...")
                        try:
                            comments_res = await client.get_note_comments(
                                note_id=note_id,
                                xsec_token=xsec_token,
                                cursor=""
                            )
                            
                            comments = comments_res.get("comments", [])
                            print(f"   ✓ 获取到 {len(comments)} 条评论")
                            
                            if comments:
                                first_comment = comments[0]
                                content = first_comment.get("content", "")
                                user = first_comment.get("user_info", {})
                                nickname = user.get("nickname", "未知")
                                print(f"     第一条评论: {nickname}: {content[:30]}...")
                        except Exception as e:
                            print(f"   ⚠ 获取评论失败: {e}")
                    
                except Exception as e:
                    print(f"   ✗ 获取笔记详情失败: {e}")
            
        except Exception as e:
            print(f"   ✗ 搜索失败: {e}")
            import traceback
            traceback.print_exc()
        
        print("\n" + "=" * 60)
        print("测试完成!")
        print("=" * 60)
        print("\n浏览器将保持打开状态10秒,然后自动关闭...")
        await asyncio.sleep(10)
        
        await browser_context.close()


if __name__ == "__main__":
    print("\n开始测试小红书爬虫...")
    print("注意: 首次运行需要扫码登录\n")
    
    try:
        asyncio.run(test_crawler())
    except KeyboardInterrupt:
        print("\n\n测试被用户中断")
    except Exception as e:
        print(f"\n\n测试出错: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n测试脚本结束")
