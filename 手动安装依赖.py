# -*- coding: utf-8 -*-
"""
手动安装依赖脚本
用于解决 requirements.txt 编码问题
"""
import subprocess
import sys

packages = [
    'flask==3.0.0',
    'flask-cors==4.0.0',
    'selenium>=4.15.0',
    'undetected-chromedriver>=3.5.0',
    'requests>=2.31.0',
    'beautifulsoup4>=4.12.0',
    'lxml>=4.9.0',
    'python-dotenv>=1.0.0',
    'fake-useragent>=1.4.0',
    'playwright>=1.45.0',
    'httpx>=0.28.1',
    'tenacity>=8.2.2',
    'pydantic>=2.5.2',
    'Pillow>=12.1.0',
    'pyhumps>=3.8.0',
]

print("=" * 60)
print("手动安装依赖包")
print("=" * 60)
print()

# 先升级 pip
print("1. 升级 pip...")
try:
    subprocess.check_call([sys.executable, '-m', 'pip', 'install', '--upgrade', 'pip'])
    print("✓ pip 升级成功")
except:
    print("⚠ pip 升级失败，继续使用当前版本")

print()
print("2. 安装依赖包...")
for i, package in enumerate(packages, 1):
    print(f"   [{i}/{len(packages)}] 安装 {package}...")
    try:
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', package, '--default-timeout=100'])
        print(f"   ✓ {package} 安装成功")
    except Exception as e:
        print(f"   ✗ {package} 安装失败: {e}")
        print(f"   继续安装其他包...")

print()
print("3. 安装 Playwright 浏览器...")
try:
    subprocess.check_call([sys.executable, '-m', 'playwright', 'install', 'chromium'])
    print("✓ Playwright 浏览器安装成功")
except Exception as e:
    print(f"✗ Playwright 浏览器安装失败: {e}")
    print("请手动运行: python -m playwright install chromium")

print()
print("=" * 60)
print("安装完成！")
print("=" * 60)
