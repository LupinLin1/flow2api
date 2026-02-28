"""
基于 RT 的本地 reCAPTCHA 打码服务 (终极闭环版 - 无 fake_useragent 纯净版)
支持：自动刷新 Session Token、外部触发指纹切换、死磕重试
"""
import os
import sys
import subprocess
# 修复 Windows 上 playwright 的 asyncio 兼容性问题
os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", "0")

import asyncio
import time
import re
import random
from pathlib import Path
from typing import Optional, Dict
from datetime import datetime
from urllib.parse import urlparse, unquote

from ..core.logger import debug_logger


# ==================== 显示环境检测 ====================
def _has_display_environment() -> bool:
    """检测是否有可用的显示环境（支持 Xvfb 虚拟显示和 macOS）"""
    import platform

    # 检查 macOS 平台（macOS 有自己的图形系统，不需要 DISPLAY）
    if platform.system() == 'Darwin':
        try:
            result = subprocess.run(['pgrep', '-x', 'WindowServer'], capture_output=True, timeout=2)
            if result.returncode == 0:
                # macOS 上 WindowServer 正在运行，说明有图形界面
                debug_logger.log_info("[BrowserCaptcha] 检测到 macOS 图形环境")
                return True
        except:
            pass

    # 检查 DISPLAY 环境变量（Linux X11）
    display = os.environ.get('DISPLAY')
    if display:
        return True

    # 检查 xvfb-run 是否可用（可选验证，用于检测 Xvfb 环境）
    try:
        result = subprocess.run(['which', 'xvfb-run'], capture_output=True, timeout=2)
        if result.returncode == 0:
            debug_logger.log_info("[BrowserCaptcha] 检测到 Xvfb 环境")
            return True
    except:
        pass

    return False


CAN_USE_HEADLESS_BROWSER = _has_display_environment()


# ==================== playwright 自动安装 ====================
def _run_pip_install(package: str, use_mirror: bool = False) -> bool:
    """运行 pip install 命令"""
    cmd = [sys.executable, '-m', 'pip', 'install', package]
    if use_mirror:
        cmd.extend(['-i', 'https://pypi.tuna.tsinghua.edu.cn/simple'])
    
    try:
        debug_logger.log_info(f"[BrowserCaptcha] 正在安装 {package}...")
        print(f"[BrowserCaptcha] 正在安装 {package}...")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if result.returncode == 0:
            debug_logger.log_info(f"[BrowserCaptcha] ✅ {package} 安装成功")
            print(f"[BrowserCaptcha] ✅ {package} 安装成功")
            return True
        else:
            debug_logger.log_warning(f"[BrowserCaptcha] {package} 安装失败: {result.stderr[:200]}")
            return False
    except Exception as e:
        debug_logger.log_warning(f"[BrowserCaptcha] {package} 安装异常: {e}")
        return False


def _run_playwright_install(use_mirror: bool = False) -> bool:
    """安装 playwright chromium 浏览器"""
    cmd = [sys.executable, '-m', 'playwright', 'install', 'chromium']
    env = os.environ.copy()
    
    if use_mirror:
        # 使用国内镜像
        env['PLAYWRIGHT_DOWNLOAD_HOST'] = 'https://npmmirror.com/mirrors/playwright'
    
    try:
        debug_logger.log_info("[BrowserCaptcha] 正在安装 chromium 浏览器...")
        print("[BrowserCaptcha] 正在安装 chromium 浏览器...")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600, env=env)
        if result.returncode == 0:
            debug_logger.log_info("[BrowserCaptcha] ✅ chromium 浏览器安装成功")
            print("[BrowserCaptcha] ✅ chromium 浏览器安装成功")
            return True
        else:
            debug_logger.log_warning(f"[BrowserCaptcha] chromium 安装失败: {result.stderr[:200]}")
            return False
    except Exception as e:
        debug_logger.log_warning(f"[BrowserCaptcha] chromium 安装异常: {e}")
        return False


def _ensure_playwright_installed() -> bool:
    """确保 playwright 已安装"""
    try:
        import playwright
        debug_logger.log_info("[BrowserCaptcha] playwright 已安装")
        return True
    except ImportError:
        pass
    
    debug_logger.log_info("[BrowserCaptcha] playwright 未安装，开始自动安装...")
    print("[BrowserCaptcha] playwright 未安装，开始自动安装...")
    
    # 先尝试官方源
    if _run_pip_install('playwright', use_mirror=False):
        return True
    
    # 官方源失败，尝试国内镜像
    debug_logger.log_info("[BrowserCaptcha] 官方源安装失败，尝试国内镜像...")
    print("[BrowserCaptcha] 官方源安装失败，尝试国内镜像...")
    if _run_pip_install('playwright', use_mirror=True):
        return True
    
    debug_logger.log_error("[BrowserCaptcha] ❌ playwright 自动安装失败，请手动安装: pip install playwright")
    print("[BrowserCaptcha] ❌ playwright 自动安装失败，请手动安装: pip install playwright")
    return False


def _ensure_browser_installed() -> bool:
    """确保 chromium 浏览器已安装"""
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            # 尝试获取浏览器路径，如果失败说明未安装
            browser_path = p.chromium.executable_path
            if browser_path and os.path.exists(browser_path):
                debug_logger.log_info(f"[BrowserCaptcha] chromium 浏览器已安装: {browser_path}")
                return True
    except Exception as e:
        debug_logger.log_info(f"[BrowserCaptcha] 检测浏览器时出错: {e}")
    
    debug_logger.log_info("[BrowserCaptcha] chromium 浏览器未安装，开始自动安装...")
    print("[BrowserCaptcha] chromium 浏览器未安装，开始自动安装...")
    
    # 先尝试官方源
    if _run_playwright_install(use_mirror=False):
        return True
    
    # 官方源失败，尝试国内镜像
    debug_logger.log_info("[BrowserCaptcha] 官方源安装失败，尝试国内镜像...")
    print("[BrowserCaptcha] 官方源安装失败，尝试国内镜像...")
    if _run_playwright_install(use_mirror=True):
        return True
    
    debug_logger.log_error("[BrowserCaptcha] ❌ chromium 浏览器自动安装失败，请手动安装: python -m playwright install chromium")
    print("[BrowserCaptcha] ❌ chromium 浏览器自动安装失败，请手动安装: python -m playwright install chromium")
    return False


# 尝试导入 playwright
async_playwright = None
Route = None
BrowserContext = None
PLAYWRIGHT_AVAILABLE = False

if not CAN_USE_HEADLESS_BROWSER:
    debug_logger.log_warning("[BrowserCaptcha] 未检测到显示环境，有头浏览器打码不可用，请使用第三方打码服务")
    print("[BrowserCaptcha] ⚠️ 未检测到显示环境，有头浏览器打码不可用")
    print("[BrowserCaptcha] 请安装 Xvfb 并使用 xvfb-run 启动程序，或使用第三方打码服务: yescaptcha, capmonster, ezcaptcha, capsolver")
else:
    if _ensure_playwright_installed():
        try:
            from playwright.async_api import async_playwright, Route, BrowserContext
            PLAYWRIGHT_AVAILABLE = True
            # 检查并安装浏览器
            _ensure_browser_installed()
        except ImportError as e:
            debug_logger.log_error(f"[BrowserCaptcha] playwright 导入失败: {e}")
            print(f"[BrowserCaptcha] ❌ playwright 导入失败: {e}")


# 配置
LABS_URL = "https://labs.google/fx/tools/flow"

# ==========================================
# 代理解析工具函数
# ==========================================
def parse_proxy_url(proxy_url: str) -> Optional[Dict[str, str]]:
    """解析代理URL"""
    if not proxy_url: return None
    if not re.match(r'^(http|https|socks5)://', proxy_url): proxy_url = f"http://{proxy_url}"
    match = re.match(r'^(socks5|http|https)://(?:([^:]+):([^@]+)@)?([^:]+):(\d+)$', proxy_url)
    if match:
        protocol, username, password, host, port = match.groups()
        proxy_config = {'server': f'{protocol}://{host}:{port}'}
        if username and password:
            proxy_config['username'] = username
            proxy_config['password'] = password
        return proxy_config
    return None

def validate_browser_proxy_url(proxy_url: str) -> tuple[bool, str]:
    if not proxy_url: return True, None
    parsed = parse_proxy_url(proxy_url)
    if not parsed: return False, "代理格式错误"
    return True, None

class TokenBrowser:
    """持久化浏览器：复用浏览器进程和上下文，保持 cookie 连续性

    架构说明：
        - 浏览器进程常驻，避免重复启动开销
        - BrowserContext 每 50 次请求后轮换，获得新 UA/指纹
        - 惰性初始化：首次调用 get_token() 时才启动浏览器
        - 异常时自动重建浏览器进程

    与临时浏览器架构的区别：
        - 旧架构：每次获取 token 都启动新浏览器（慢）
        - 新架构：复用浏览器进程，仅在必要时轮换 context（快）

    线程安全：
        - 并发控制由服务层的 semaphore 管理
        - 多个 TokenBrowser 实例之间独立运行
    """
    
    # UA 池
    UA_LIST = [
        # Windows Chrome (120-132)
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        # Windows Chrome 完整版本号
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.6834.83 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.6778.139 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.6723.117 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.6668.100 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.6613.138 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.6533.120 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.6478.127 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.6422.141 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        # Windows Edge (120-132)
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36 Edg/132.0.0.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36 Edg/130.0.0.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36 Edg/129.0.0.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36 Edg/128.0.0.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36 Edg/127.0.0.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36 Edg/126.0.0.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36 Edg/125.0.0.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 Edg/124.0.0.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36 Edg/123.0.0.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.6834.83 Safari/537.36 Edg/132.0.2957.115",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.6778.139 Safari/537.36 Edg/131.0.2903.99",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.6723.117 Safari/537.36 Edg/130.0.2849.80",
        # macOS Chrome (120-132)
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_3_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_2_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_6_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_5_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
        # macOS Safari
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Safari/605.1.15",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_3_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3.1 Safari/605.1.15",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_2_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2.1 Safari/605.1.15",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_6_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Safari/605.1.15",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.2 Safari/605.1.15",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.1 Safari/605.1.15",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Safari/605.1.15",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.6 Safari/605.1.15",
        # macOS Edge
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36 Edg/132.0.0.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36 Edg/130.0.0.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36 Edg/129.0.0.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36 Edg/132.0.0.0",
        # Linux Chrome
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Ubuntu; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Ubuntu; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Ubuntu; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
        # Linux Firefox
        "Mozilla/5.0 (X11; Linux x86_64; rv:134.0) Gecko/20100101 Firefox/134.0",
        "Mozilla/5.0 (X11; Linux x86_64; rv:133.0) Gecko/20100101 Firefox/133.0",
        "Mozilla/5.0 (X11; Linux x86_64; rv:132.0) Gecko/20100101 Firefox/132.0",
        "Mozilla/5.0 (X11; Linux x86_64; rv:131.0) Gecko/20100101 Firefox/131.0",
        "Mozilla/5.0 (X11; Linux x86_64; rv:130.0) Gecko/20100101 Firefox/130.0",
        "Mozilla/5.0 (X11; Linux x86_64; rv:129.0) Gecko/20100101 Firefox/129.0",
        "Mozilla/5.0 (X11; Linux x86_64; rv:128.0) Gecko/20100101 Firefox/128.0",
        "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:134.0) Gecko/20100101 Firefox/134.0",
        "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:133.0) Gecko/20100101 Firefox/133.0",
        "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:132.0) Gecko/20100101 Firefox/132.0",
        "Mozilla/5.0 (X11; Fedora; Linux x86_64; rv:134.0) Gecko/20100101 Firefox/134.0",
        # Windows Firefox
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:134.0) Gecko/20100101 Firefox/134.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:133.0) Gecko/20100101 Firefox/133.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:132.0) Gecko/20100101 Firefox/132.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:131.0) Gecko/20100101 Firefox/131.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:130.0) Gecko/20100101 Firefox/130.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:129.0) Gecko/20100101 Firefox/129.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:128.0) Gecko/20100101 Firefox/128.0",
        # macOS Firefox
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 14.4; rv:134.0) Gecko/20100101 Firefox/134.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 14.3; rv:133.0) Gecko/20100101 Firefox/133.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 14.2; rv:132.0) Gecko/20100101 Firefox/132.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:134.0) Gecko/20100101 Firefox/134.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:133.0) Gecko/20100101 Firefox/133.0",
        # Opera
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 OPR/116.0.0.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36 OPR/115.0.0.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36 OPR/114.0.0.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36 OPR/113.0.0.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36 OPR/112.0.0.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 OPR/116.0.0.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36 OPR/115.0.0.0",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 OPR/116.0.0.0",
        # Brave
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 Brave/131",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36 Brave/130",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 Brave/131",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 Brave/131",
        # Vivaldi
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36 Vivaldi/6.9.3447.54",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36 Vivaldi/6.8.3381.55",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36 Vivaldi/6.9.3447.54",
    ]
    
    # 分辨率池
    RESOLUTIONS = [
        (1920, 1080), (2560, 1440), (3840, 2160), (1366, 768), (1536, 864),
        (1600, 900), (1280, 720), (1360, 768), (1920, 1200),
        (1440, 900), (1680, 1050), (1280, 800), (2560, 1600),
        (2880, 1800), (3024, 1890), (3456, 2160),
        (1280, 1024), (1024, 768), (1400, 1050),
        (1920, 1280), (2736, 1824), (2880, 1920), (3000, 2000),
        (2256, 1504), (2496, 1664), (3240, 2160),
        (3200, 1800), (2304, 1440), (1800, 1200),
    ]
    
    def __init__(self, token_id: int, user_data_dir: str, db=None):
        self.token_id = token_id
        self.user_data_dir = user_data_dir
        self.db = db
        # 注意：移除了 self._semaphore，避免与 BrowserCaptchaService._token_semaphore 形成双重锁定
        # 并发控制由服务层统一管理
        self._solve_count = 0
        self._error_count = 0
        # 持久化浏览器状态
        self._playwright = None
        self._browser = None
        self._context = None
        self._request_count = 0
        self._max_requests_per_context = 50  # 每 50 次请求轮换 context

    async def _get_proxy_option(self) -> Optional[Dict[str, str]]:
        """获取代理配置"""
        try:
            if self.db:
                captcha_config = await self.db.get_captcha_config()
                if captcha_config:  # 检查 None
                    raw_url = (captcha_config.browser_proxy_enabled and
                              captcha_config.browser_proxy_url)
                    if raw_url:
                        proxy_option = parse_proxy_url(raw_url.strip())
                        if proxy_option:
                            debug_logger.log_info(f"[BrowserCaptcha] Token-{self.token_id} 使用代理: {proxy_option['server']}")
                            return proxy_option
        except Exception as e:
            debug_logger.log_warning(f"[BrowserCaptcha] Token-{self.token_id} 获取代理配置失败: {type(e).__name__}: {str(e)[:100]}")
        return None

    async def _ensure_browser(self):
        """确保浏览器进程已启动（惰性初始化）"""
        if self._browser and self._playwright:
            return
        # 清理旧的残留
        await self._close_browser_only()

        self._playwright = await async_playwright().start()
        Path(self.user_data_dir).mkdir(parents=True, exist_ok=True)

        proxy_option = await self._get_proxy_option()
        base_w, base_h = random.choice(self.RESOLUTIONS)
        width, height = base_w, base_h - random.randint(0, 80)

        self._browser = await self._playwright.chromium.launch(
            headless=False,
            proxy=proxy_option,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--no-sandbox',
                '--disable-dev-shm-usage',
                '--disable-setuid-sandbox',
                '--no-first-run',
                '--no-zygote',
                f'--window-size={width},{height}',
                '--disable-infobars',
                '--hide-scrollbars',
            ]
        )
        debug_logger.log_info(f"[BrowserCaptcha] Token-{self.token_id} 浏览器进程已启动")

    async def _get_or_create_context(self):
        """获取或创建浏览器上下文，到期后轮换"""
        await self._ensure_browser()

        # 检查是否需要轮换 context
        if self._context and self._request_count < self._max_requests_per_context:
            self._request_count += 1
            return self._context

        # 关闭旧 context
        if self._context:
            try:
                await self._context.close()
            except:
                pass
            debug_logger.log_info(f"[BrowserCaptcha] Token-{self.token_id} 轮换 context（已用 {self._request_count} 次）")

        random_ua = random.choice(self.UA_LIST)
        base_w, base_h = random.choice(self.RESOLUTIONS)
        width, height = base_w, base_h - random.randint(0, 80)
        viewport = {"width": width, "height": height}

        self._context = await self._browser.new_context(
            user_agent=random_ua,
            viewport=viewport,
        )
        self._request_count = 1
        return self._context

    async def _close_browser_only(self):
        """关闭浏览器进程和 context，供内部使用"""
        try:
            if self._context:
                await self._context.close()
        except Exception as e:
            debug_logger.log_warning(f"[BrowserCaptcha] Token-{self.token_id} 关闭 context 失败: {type(e).__name__}: {str(e)[:100]}")
        self._context = None
        try:
            if self._browser:
                await self._browser.close()
        except Exception as e:
            debug_logger.log_warning(f"[BrowserCaptcha] Token-{self.token_id} 关闭 browser 失败: {type(e).__name__}: {str(e)[:100]}")
        self._browser = None
        try:
            if self._playwright:
                await self._playwright.stop()
        except Exception as e:
            debug_logger.log_warning(f"[BrowserCaptcha] Token-{self.token_id} 停止 playwright 失败: {type(e).__name__}: {str(e)[:100]}")
        self._playwright = None
        self._request_count = 0

    async def close(self):
        """公开的关闭方法"""
        await self._close_browser_only()
    
    async def _simulate_human_behavior(self, page):
        """模拟人类浏览行为，提升 reCAPTCHA v3 评分"""
        try:
            viewport = page.viewport_size or {"width": 1920, "height": 1080}
            w, h = viewport["width"], viewport["height"]

            # 初始延迟 - 模拟用户看到页面后的反应时间
            await asyncio.sleep(random.uniform(0.5, 1.5))

            # 随机鼠标移动 2-4 次
            for _ in range(random.randint(2, 4)):
                x = random.randint(100, w - 100)
                y = random.randint(100, h - 100)
                await page.mouse.move(x, y, steps=random.randint(3, 8))
                await asyncio.sleep(random.uniform(0.1, 0.4))

            # 随机滚动
            await page.mouse.wheel(0, random.randint(50, 200))
            await asyncio.sleep(random.uniform(0.2, 0.5))

            # 尝试点击 textarea（模拟用户准备输入）
            try:
                textarea = page.locator("textarea").first
                if await textarea.is_visible(timeout=500):
                    await textarea.click()
                    await asyncio.sleep(random.uniform(0.2, 0.5))
            except Exception as e:
                debug_logger.log_debug(f"[BrowserCaptcha] Token-{self.token_id} 点击 textarea 失败: {type(e).__name__}")

            # 最后再移一下鼠标
            await page.mouse.move(
                random.randint(200, w - 200),
                random.randint(200, h - 200),
                steps=random.randint(3, 6)
            )
            await asyncio.sleep(random.uniform(0.3, 0.8))
        except Exception as e:
            # 行为模拟失败不影响主流程，但记录日志便于调试
            debug_logger.log_debug(f"[BrowserCaptcha] Token-{self.token_id} 行为模拟失败: {type(e).__name__}: {str(e)[:100]}")

    async def _execute_captcha(self, context, project_id: str, website_key: str, action: str) -> Optional[str]:
        """在给定 context 中执行打码逻辑"""
        page = None
        try:
            page = await context.new_page()
            await page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined});")
            
            page_url = f"https://labs.google/fx/tools/flow/project/{project_id}"
            
            async def handle_route(route):
                if route.request.url.rstrip('/') == page_url.rstrip('/'):
                    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Flow - Google Labs</title>
    <meta name="description" content="Create videos and images with AI using Flow on Google Labs">
    <link rel="icon" href="https://labs.google/favicon.ico">
    <script src="https://www.google.com/recaptcha/enterprise.js?render={website_key}"></script>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: 'Google Sans', Roboto, Arial, sans-serif; background: #131314; color: #e3e3e3; min-height: 100vh; }}
        header {{ display: flex; align-items: center; padding: 12px 24px; border-bottom: 1px solid #3c4043; }}
        header .logo {{ font-size: 18px; font-weight: 500; color: #8ab4f8; }}
        header nav {{ margin-left: auto; display: flex; gap: 16px; }}
        header nav a {{ color: #9aa0a6; text-decoration: none; font-size: 14px; }}
        .main {{ max-width: 960px; margin: 40px auto; padding: 0 24px; }}
        .project-title {{ font-size: 28px; font-weight: 400; margin-bottom: 24px; }}
        .prompt-area {{ background: #1e1f20; border-radius: 12px; padding: 20px; margin-bottom: 24px; }}
        .prompt-input {{ width: 100%; background: transparent; border: none; color: #e3e3e3; font-size: 16px; outline: none; resize: none; min-height: 60px; font-family: inherit; }}
        .prompt-input::placeholder {{ color: #5f6368; }}
        .toolbar {{ display: flex; align-items: center; gap: 12px; margin-top: 16px; }}
        .btn {{ padding: 8px 24px; border-radius: 20px; border: none; font-size: 14px; cursor: pointer; font-family: inherit; }}
        .btn-primary {{ background: #8ab4f8; color: #202124; }}
        .btn-secondary {{ background: #3c4043; color: #e3e3e3; }}
        .gallery {{ display: grid; grid-template-columns: repeat(2, 1fr); gap: 16px; }}
        .gallery-item {{ background: #1e1f20; border-radius: 8px; aspect-ratio: 16/9; }}
        .footer {{ text-align: center; color: #5f6368; font-size: 12px; padding: 24px; margin-top: 40px; }}
    </style>
</head>
<body>
    <header>
        <div class="logo">Flow</div>
        <nav>
            <a href="#">My projects</a>
            <a href="#">Gallery</a>
        </nav>
    </header>
    <div class="main">
        <h1 class="project-title">My Project</h1>
        <div class="prompt-area">
            <textarea class="prompt-input" placeholder="Describe what you want to create..." rows="3"></textarea>
            <div class="toolbar">
                <button class="btn btn-primary">Generate</button>
                <button class="btn btn-secondary">Settings</button>
            </div>
        </div>
        <div class="gallery">
            <div class="gallery-item"></div>
            <div class="gallery-item"></div>
            <div class="gallery-item"></div>
            <div class="gallery-item"></div>
        </div>
    </div>
    <div class="footer">Google Labs &middot; Experiment responsibly</div>
</body>
</html>"""
                    await route.fulfill(status=200, content_type="text/html", body=html)
                elif any(d in route.request.url for d in ["google.com", "gstatic.com", "recaptcha.net"]):
                    await route.continue_()
                else:
                    await route.abort()
            
            await page.route("**/*", handle_route)
            try:
                await page.goto(page_url, wait_until="load", timeout=30000)
            except Exception as e:
                debug_logger.log_warning(f"[BrowserCaptcha] Token-{self.token_id} page.goto 失败: {type(e).__name__}: {str(e)[:200]}")
                return None
            
            try:
                await page.wait_for_function("typeof grecaptcha !== 'undefined'", timeout=15000)
            except Exception as e:
                debug_logger.log_warning(f"[BrowserCaptcha] Token-{self.token_id} grecaptcha 未就绪: {type(e).__name__}: {str(e)[:200]}")
                return None

            # 模拟人类行为，提升 reCAPTCHA v3 评分
            await self._simulate_human_behavior(page)

            token = await asyncio.wait_for(
                page.evaluate(f"""
                    (actionName) => {{
                        return new Promise((resolve, reject) => {{
                            const timeout = setTimeout(() => reject(new Error('timeout')), 25000);
                            grecaptcha.enterprise.execute('{website_key}', {{action: actionName}})
                                .then(t => {{ resolve(t); }})
                                .catch(e => {{ reject(e); }});
                        }});
                    }}
                """, action),
                timeout=30
            )
            return token
        except Exception as e:
            msg = f"{type(e).__name__}: {str(e)}"
            debug_logger.log_warning(f"[BrowserCaptcha] Token-{self.token_id} 打码失败: {msg[:200]}")
            return None
        finally:
            if page:
                try:
                    await page.close()
                except Exception as e:
                    debug_logger.log_warning(f"[BrowserCaptcha] Token-{self.token_id} 关闭页面失败: {type(e).__name__}: {str(e)[:100]}")
    
    async def get_token(self, project_id: str, website_key: str, action: str = "IMAGE_GENERATION") -> Optional[str]:
        """获取 Token：复用持久化浏览器上下文

        Args:
            project_id: Flow 项目 ID
            website_key: reCAPTCHA website key
            action: reCAPTCHA action 名称，默认 "IMAGE_GENERATION"

        Returns:
            成功时返回 reCAPTCHA token 字符串，失败返回 None

        Note:
            - 最多重试 3 次
            - 异常时重建浏览器进程
            - 并发控制由服务层的 semaphore 管理
        """
        MAX_RETRIES = 3

        for attempt in range(MAX_RETRIES):
            try:
                start_ts = time.time()

                context = await self._get_or_create_context()

                # 执行打码
                token = await self._execute_captcha(context, project_id, website_key, action)

                if token:
                    self._solve_count += 1
                    debug_logger.log_info(f"[BrowserCaptcha] Token-{self.token_id} 获取成功 ({(time.time()-start_ts)*1000:.0f}ms)")
                    return token

                self._error_count += 1
                debug_logger.log_warning(f"[BrowserCaptcha] Token-{self.token_id} 尝试 {attempt+1}/{MAX_RETRIES} 失败")

            except Exception as e:
                self._error_count += 1
                debug_logger.log_error(f"[BrowserCaptcha] Token-{self.token_id} 浏览器错误: {type(e).__name__}: {str(e)[:200]}")
                # 浏览器异常时强制重建
                await self._close_browser_only()

            # 重试前等待
            if attempt < MAX_RETRIES - 1:
                await asyncio.sleep(1)

        return None
    

class BrowserCaptchaService:
    """多浏览器轮询打码服务（单例模式）
    
    支持配置浏览器数量，每个浏览器只开 1 个标签页，请求轮询分配
    """
    
    _instance: Optional['BrowserCaptchaService'] = None
    _lock = asyncio.Lock()
    
    def __init__(self, db=None):
        self.db = db
        self.website_key = "6LdsFiUsAAAAAIjVDZcuLhaHiDn5nnHVXVRQGeMV"
        self.base_user_data_dir = os.path.join(os.getcwd(), "browser_data_rt")
        self._browsers: Dict[int, TokenBrowser] = {}
        self._browsers_lock = asyncio.Lock()
        
        # 浏览器数量配置
        self._browser_count = 1  # 默认 1 个，会从数据库加载
        self._round_robin_index = 0  # 轮询索引
        
        # 统计指标
        self._stats = {
            "req_total": 0,
            "gen_ok": 0,
            "gen_fail": 0,
            "api_403": 0
        }
        
        # 并发限制将在 _load_browser_count 中根据配置设置
        self._token_semaphore = None
    
    @classmethod
    async def get_instance(cls, db=None) -> 'BrowserCaptchaService':
        # 直接获取锁，避免竞态条件
        async with cls._lock:
            if cls._instance is None:
                cls._instance = cls(db)
                # 在锁内完成初始化（包括异步操作）
                await cls._instance._load_browser_count()
        return cls._instance
    
    def _check_available(self):
        """检查服务是否可用"""
        if not CAN_USE_HEADLESS_BROWSER:
            raise RuntimeError(
                "有头浏览器打码在当前环境中不可用（缺少显示环境）。"
                "请安装 Xvfb 并使用 xvfb-run 启动程序，或使用第三方打码服务: yescaptcha, capmonster, ezcaptcha, capsolver"
            )
        if not PLAYWRIGHT_AVAILABLE or async_playwright is None:
            raise RuntimeError(
                "playwright 未安装或不可用。"
                "请手动安装: pip install playwright && python -m playwright install chromium"
            )
    
    async def _load_browser_count(self):
        """从数据库加载浏览器数量配置"""
        if self.db:
            try:
                captcha_config = await self.db.get_captcha_config()
                self._browser_count = max(1, captcha_config.browser_count)
                debug_logger.log_info(f"[BrowserCaptcha] 浏览器数量配置: {self._browser_count}")
            except Exception as e:
                debug_logger.log_warning(f"[BrowserCaptcha] 加载 browser_count 配置失败: {e}，使用默认值 1")
                self._browser_count = 1
        # 并发限制 = 浏览器数量，不再硬编码限制
        self._token_semaphore = asyncio.Semaphore(self._browser_count)
        debug_logger.log_info(f"[BrowserCaptcha] 并发上限: {self._browser_count}")
    
    async def reload_browser_count(self):
        """重新加载浏览器数量配置（用于配置更新后热重载）"""
        old_count = self._browser_count
        await self._load_browser_count()
        
        # 如果数量减少，移除多余的浏览器实例
        if self._browser_count < old_count:
            async with self._browsers_lock:
                for browser_id in list(self._browsers.keys()):
                    if browser_id >= self._browser_count:
                        self._browsers.pop(browser_id)
                        debug_logger.log_info(f"[BrowserCaptcha] 移除多余浏览器实例 {browser_id}")
    
    def _log_stats(self):
        total = self._stats["req_total"]
        gen_fail = self._stats["gen_fail"]
        api_403 = self._stats["api_403"]
        gen_ok = self._stats["gen_ok"]
        
        valid_success = gen_ok - api_403
        if valid_success < 0: valid_success = 0
        
        rate = (valid_success / total * 100) if total > 0 else 0.0

    
    async def _get_or_create_browser(self, browser_id: int) -> TokenBrowser:
        """获取或创建指定 ID 的浏览器实例"""
        async with self._browsers_lock:
            if browser_id not in self._browsers:
                user_data_dir = os.path.join(self.base_user_data_dir, f"browser_{browser_id}")
                browser = TokenBrowser(browser_id, user_data_dir, db=self.db)
                self._browsers[browser_id] = browser
                debug_logger.log_info(f"[BrowserCaptcha] 创建浏览器实例 {browser_id}")
            return self._browsers[browser_id]
    
    def _get_next_browser_id(self) -> int:
        """轮询获取下一个浏览器 ID"""
        browser_id = self._round_robin_index % self._browser_count
        self._round_robin_index += 1
        return browser_id
    
    async def get_token(self, project_id: str, action: str = "IMAGE_GENERATION", token_id: int = None) -> tuple[Optional[str], int]:
        """获取 reCAPTCHA Token（轮询分配到不同浏览器）
        
        Args:
            project_id: 项目 ID
            action: reCAPTCHA action
            token_id: 忽略，使用轮询分配
        
        Returns:
            (token, browser_id) 元组，调用方失败时用 browser_id 调用 report_error
        """
        # 检查服务是否可用
        self._check_available()
        
        self._stats["req_total"] += 1
        
        # 全局并发限制（如果已配置）
        if self._token_semaphore:
            async with self._token_semaphore:
                # 轮询选择浏览器
                browser_id = self._get_next_browser_id()
                browser = await self._get_or_create_browser(browser_id)
                
                token = await browser.get_token(project_id, self.website_key, action)
            
            if token:
                self._stats["gen_ok"] += 1
            else:
                self._stats["gen_fail"] += 1
                
            self._log_stats()
            return token, browser_id
        
        # 无并发限制时直接执行
        browser_id = self._get_next_browser_id()
        browser = await self._get_or_create_browser(browser_id)
        
        token = await browser.get_token(project_id, self.website_key, action)
        
        if token:
            self._stats["gen_ok"] += 1
        else:
            self._stats["gen_fail"] += 1
            
        self._log_stats()
        return token, browser_id

    async def report_error(self, browser_id: int = None):
        """上层举报：Token 无效（统计用）

        Args:
            browser_id: 浏览器 ID（用于日志记录和错误追踪）

        Note:
            当前使用持久化浏览器架构，browser_id 用于标识哪个浏览器实例产生了无效 token
        """
        async with self._browsers_lock:
            self._stats["api_403"] += 1
            if browser_id is not None:
                debug_logger.log_info(f"[BrowserCaptcha] 浏览器 {browser_id} 的 token 验证失败")

    async def remove_browser(self, browser_id: int):
        """移除指定浏览器实例并关闭其资源

        Args:
            browser_id: 要移除的浏览器 ID

        Note:
            此方法会调用 browser.close() 清理资源
        """
        async with self._browsers_lock:
            browser = self._browsers.pop(browser_id, None)
            if browser:
                await browser.close()

    async def refresh_session_token(self, project_id: str) -> Optional[str]:
        """刷新 Session Token（Browser 模式）

        使用 Playwright 浏览器访问 Flow AI 页面，从 cookies 中提取
        __Secure-next-auth.session-token

        Args:
            project_id: 项目 ID

        Returns:
            新的 Session Token，失败返回 None
        """
        import playwright.async_api as playwright_api

        start_time = time.time()
        debug_logger.log_info(f"[BrowserCaptcha] 开始刷新 Session Token (project: {project_id})...")

        self._check_available()

        # 使用第一个浏览器实例
        browser_id = 0
        browser = await self._get_or_create_browser(browser_id)

        try:
            # 获取或创建浏览器上下文
            context = await browser._get_or_create_context()

            # 创建新页面
            page = await context.new_page()
            page_url = f"https://labs.google/fx/tools/flow/project/{project_id}"

            try:
                # 导航到 Flow AI 页面
                debug_logger.log_info(f"[BrowserCaptcha] 导航到 {page_url}...")
                await page.goto(page_url, wait_until="load", timeout=30000)

                # 等待页面加载完成
                await page.wait_for_load_state("networkidle", timeout=10000)

                # 额外等待确保 cookies 已设置
                await asyncio.sleep(2)

                # 从 cookies 中提取 __Secure-next-auth.session-token
                session_token = None

                # 使用 Playwright 的 cookies API
                cookies = await context.cookies()
                for cookie in cookies:
                    if cookie.get("name") == "__Secure-next-auth.session-token":
                        session_token = cookie.get("value")
                        debug_logger.log_info(f"[BrowserCaptcha] 找到 Session Token (长度: {len(session_token) if session_token else 0})")
                        break

                duration_ms = (time.time() - start_time) * 1000

                if session_token:
                    debug_logger.log_info(f"[BrowserCaptcha] ✅ Session Token 获取成功（耗时 {duration_ms:.0f}ms）")
                    return session_token
                else:
                    debug_logger.log_error(f"[BrowserCaptcha] ❌ 未找到 __Secure-next-auth.session-token cookie")
                    return None

            except Exception as e:
                debug_logger.log_error(f"[BrowserCaptcha] 刷新 Session Token 失败: {type(e).__name__}: {str(e)[:200]}")
                return None
            finally:
                # 关闭页面
                try:
                    await page.close()
                except Exception:
                    pass

        except Exception as e:
            debug_logger.log_error(f"[BrowserCaptcha] 刷新 Session Token 异常: {type(e).__name__}: {str(e)[:200]}")
            return None

    async def close(self):
        """关闭所有浏览器实例并清理资源"""
        async with self._browsers_lock:
            for browser in self._browsers.values():
                await browser.close()
            self._browsers.clear()
            
    async def open_login_browser(self): return {"success": False, "error": "Not implemented"}
    async def create_browser_for_token(self, t, s=None): pass
    def get_stats(self): 
        base_stats = {
            "total_solve_count": self._stats["gen_ok"],
            "total_error_count": self._stats["gen_fail"],
            "risk_403_count": self._stats["api_403"],
            "browser_count": len(self._browsers),
            "configured_browser_count": self._browser_count,
            "browsers": []
        }
        return base_stats
