# -*- coding: utf-8 -*-
"""
HidenCloud 自动续期 - Python Infinicloud版
"""
import os
import sys
import time
import json
import random
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

# ================= 配置常量 =================
RENEW_DAYS = 7
CACHE_FILE_NAME = 'hiden_cookies.json'
LOCAL_CACHE_PATH = os.path.join(os.path.dirname(__file__), CACHE_FILE_NAME)

# ================= 消息推送模块 =================
def send_notify(text, desp):
    token = os.environ.get("WP_APP_TOKEN_ONE")
    uids_str = os.environ.get("WP_UIDs")
    
    if not token or not uids_str:
        print("⚠️ 未配置 WxPusher，跳过推送")
        return

    print(f"\n==== 开始推送通知: {text} ====\n")
    
    # 处理分隔符: 支持逗号、分号、换行
    import re
    uids = [u.strip() for u in re.split(r'[,;\n]', uids_str) if u.strip()]
    
    url = 'https://wxpusher.zjiecode.com/api/send/message'
    data = {
        "appToken": token,
        "content": f"<h3>{text}</h3><br>{desp.replace(chr(10), '<br>')}",
        "summary": text,
        "contentType": 2, # HTML
        "uids": uids
    }
    
    try:
        res = requests.post(url, json=data)
        if res.status_code == 200:
            print("✅ WxPusher 推送成功")
        else:
            print(f"❌ WxPusher 推送响应: {res.text}")
    except Exception as e:
        print(f"❌ WxPusher 推送失败: {e}")

# ================= WebDAV 模块 =================
class WebDavManager:
    def __init__(self):
        self.url = os.environ.get("WEBDAV_URL", "")
        self.user = os.environ.get("WEBDAV_USER")
        self.password = os.environ.get("WEBDAV_PASS")
        
        if self.url and not self.url.endswith('/'):
            self.url += '/'
        self.full_url = self.url + CACHE_FILE_NAME if self.url else ""

    def download(self):
        if not self.url or not self.user:
            print("⚠️ 未配置 WebDAV，跳过云端同步")
            return
            
        print("☁️ 正在从 Infinicloud 下载缓存...")
        try:
            res = requests.get(self.full_url, auth=(self.user, self.password), timeout=30)
            if res.status_code == 200:
                with open(LOCAL_CACHE_PATH, 'w', encoding='utf-8') as f:
                    f.write(res.text)
                print("✅ 云端缓存下载成功")
            elif res.status_code == 404:
                print("⚪ 云端暂无缓存文件 (首次运行)")
            else:
                print(f"⚠️ 下载失败，状态码: {res.status_code}")
        except Exception as e:
            print(f"❌ WebDAV 下载错误: {e}")

    def upload(self, data):
        if not self.url or not self.user:
            return
        
        print("☁️ 正在上传最新缓存到 Infinicloud...")
        try:
            json_str = json.dumps(data, indent=2)
            res = requests.put(
                self.full_url, 
                data=json_str, 
                auth=(self.user, self.password),
                headers={'Content-Type': 'application/json'},
                timeout=30
            )
            if res.status_code in [200, 201, 204]:
                print("✅ 云端缓存上传成功")
            else:
                print(f"❌ WebDAV 上传失败: {res.status_code}")
        except Exception as e:
            print(f"❌ WebDAV 上传错误: {e}")

# ================= 辅助工具 =================
def sleep_random(min_ms=3000, max_ms=8000):
    sec = random.randint(min_ms, max_ms) / 1000.0
    time.sleep(sec)

class CacheManager:
    @staticmethod
    def load():
        if os.path.exists(LOCAL_CACHE_PATH):
            try:
                with open(LOCAL_CACHE_PATH, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                print("读取本地缓存失败")
        return {}

    @staticmethod
    def update(index, cookie_str):
        dav = WebDavManager()
        data = CacheManager.load()
        # 索引转字符串key
        key = str(index)
        
        if data.get(key) != cookie_str:
            data[key] = cookie_str
            with open(LOCAL_CACHE_PATH, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
            print(f"💾 [账号 {index + 1}] 本地缓存已更新")
            dav.upload(data)

# ================= 核心机器人类 =================
class HidenCloudBot:
    def __init__(self, env_cookie, index):
        self.index = index + 1
        self.base_url = "https://dash.hidencloud.com"
        self.session = requests.Session()
        self.csrf_token = ""
        self.services = []
        
        # 配置 Headers
        self.session.headers.update({
            'Host': 'dash.hidencloud.com',
            'Connection': 'keep-alive',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Referer': 'https://dash.hidencloud.com/',
        })

        # 加载 Cookie (优先缓存)
        cached_data = CacheManager.load()
        cached_cookie = cached_data.get(str(index))
        
        if cached_cookie:
            self.log("发现本地缓存 Cookie，优先使用...")
            self.load_cookie_str(cached_cookie)
        else:
            self.log("使用环境变量 Cookie...")
            self.load_cookie_str(env_cookie)

    def log(self, msg):
        print(f"[账号 {self.index}] {msg}")

    def load_cookie_str(self, cookie_str):
        """解析 cookie 字符串到 session"""
        if not cookie_str:
            return
        cookie_dict = {}
        for item in cookie_str.split(';'):
            if '=' in item:
                k, v = item.split('=', 1)
                cookie_dict[k.strip()] = v.strip()
        self.session.cookies.update(cookie_dict)

    def get_cookie_str(self):
        """从 session 导出 cookie 字符串"""
        return '; '.join([f"{c.name}={c.value}" for c in self.session.cookies])

    def save_current_cookies(self):
        """保存当前会话的 Cookie 到缓存"""
        CacheManager.update(self.index - 1, self.get_cookie_str())

    def reset_to_env(self, env_cookie):
        """重置为环境变量 Cookie"""
        self.session.cookies.clear()
        self.load_cookie_str(env_cookie)
        self.log("切换回环境变量原始 Cookie 重试...")

    def request(self, method, url, data=None, headers=None):
        """封装请求，自动处理 URL 和 错误"""
        full_url = urljoin(self.base_url, url)
        try:
            resp = self.session.request(method, full_url, data=data, headers=headers, timeout=30)
            # 每次请求后尝试更新缓存（如果有新cookie）
            self.save_current_cookies()
            return resp
        except Exception as e:
            self.log(f"请求异常: {e}")
            raise

    def init(self):
        self.log("正在验证登录状态...")
        try:
            res = self.request('GET', '/dashboard')
            
            # 检查重定向是否到了登录页
            if '/login' in res.url:
                self.log("❌ 当前 Cookie 已失效")
                return False

            soup = BeautifulSoup(res.text, 'html.parser')

            # =========== 新增这一行进行调试 ===========
            print(f"👀 [调试] 网页标题是: {soup.title.string if soup.title else '无标题'}")
            # ========================================
            
            # 提取 CSRF Token
            token_tag = soup.find('meta', attrs={'name': 'csrf-token'})
            if token_tag:
                self.csrf_token = token_tag['content']

            # 解析服务列表
            self.services = []
            for a in soup.find_all('a', href=True):
                href = a['href']
                if '/service/' in href and '/manage' in href:
                    svc_id = href.split('/service/')[1].split('/')[0]
                    if not any(s['id'] == svc_id for s in self.services):
                        self.services.append({'id': svc_id, 'url': href})

            self.log(f"✅ 登录成功，发现 {len(self.services)} 个服务。")
            return True
        except Exception as e:
            self.log(f"❌ 初始化异常: {e}")
            return False

    def process_service(self, service):
        sleep_random(2000, 4000)
        self.log(f">>> 处理服务 ID: {service['id']}")

        try:
            # 1. 获取管理页面 (提取 form token)
            manage_res = self.request('GET', f"/service/{service['id']}/manage")
            soup = BeautifulSoup(manage_res.text, 'html.parser')
            token_input = soup.find('input', attrs={'name': '_token'})
            
            if not token_input:
                self.log("❌ 无法找到续期 Token")
                return

            form_token = token_input['value']
            self.log(f"提交续期 ({RENEW_DAYS}天)...")
            sleep_random(1000, 2000)

            # 2. 提交续期请求
            payload = {
                '_token': form_token,
                'days': RENEW_DAYS
            }
            headers = {
                'X-CSRF-TOKEN': self.csrf_token,
                'Referer': f"https://dash.hidencloud.com/service/{service['id']}/manage"
            }
            
            res = self.request('POST', f"/service/{service['id']}/renew", data=payload, headers=headers)

            if '/invoice/' in res.url:
                self.log("⚡️ 续期成功，前往支付")
                self.perform_pay_from_html(res.text, res.url)
            else:
                self.log("⚠️ 续期后未跳转，检查列表...")
                self.check_and_pay_invoices(service['id'])

        except Exception as e:
            self.log(f"处理异常: {e}")

    def check_and_pay_invoices(self, service_id):
        sleep_random(2000, 3000)
        try:
            res = self.request('GET', f"/service/{service_id}/invoices?where=unpaid")
            soup = BeautifulSoup(res.text, 'html.parser')
            
            invoice_links = []
            for a in soup.find_all('a', href=True):
                if '/invoice/' in a['href'] and 'download' not in a['href']:
                    invoice_links.append(a['href'])
            
            unique_invoices = list(set(invoice_links))
            
            if not unique_invoices:
                self.log("✅ 无未支付账单")
                return

            for url in unique_invoices:
                self.pay_single_invoice(url)
                sleep_random(3000, 5000)
        except Exception as e:
            self.log(f"查账单出错: {e}")

    def pay_single_invoice(self, url):
        try:
            self.log(f"📄 打开账单: {url}")
            res = self.request('GET', url)
            self.perform_pay_from_html(res.text, url)
        except Exception as e:
            self.log(f"访问账单失败: {e}")

    def perform_pay_from_html(self, html_content, current_url):
        soup = BeautifulSoup(html_content, 'html.parser')
        
        target_form = None
        target_action = ""

        # 查找包含 "pay" 按钮的表单
        for form in soup.find_all('form'):
            btn = form.find('button')
            if btn and 'pay' in btn.get_text().lower():
                action = form.get('action', '')
                if action and 'balance/add' not in action:
                    target_form = form
                    target_action = action
                    break
        
        if not target_form:
            self.log("⚪ 页面未找到支付表单 (可能已支付)。")
            return

        # 提取表单数据
        payload = {}
        for inp in target_form.find_all('input'):
            name = inp.get('name')
            value = inp.get('value', '')
            if name:
                payload[name] = value

        self.log("👉 提交支付...")
        try:
            headers = {
                'X-CSRF-TOKEN': self.csrf_token,
                'Referer': current_url
            }
            res = self.request('POST', target_action, data=payload, headers=headers)
            
            if res.status_code == 200:
                self.log("✅ 支付成功！")
            else:
                self.log(f"⚠️ 支付响应: {res.status_code}")
        except Exception as e:
            self.log(f"❌ 支付失败: {e}")

# ================= 主程序 =================
if __name__ == '__main__':
    # 从环境变量读取
    env_cookies = os.environ.get("HIDEN_COOKIE", "")
    import re
    cookies_list = re.split(r'[&\n]', env_cookies)
    cookies_list = [c for c in cookies_list if c.strip()]

    if not cookies_list:
        print("❌ 未配置环境变量 HIDEN_COOKIE")
        sys.exit(0)

    # 1. 下载云端缓存
    WebDavManager().download()

    print(f"\n=== HidenCloud 续期脚本启动 (Python版) ===")
    summary_msg = ""

    for i, cookie in enumerate(cookies_list):
        bot = HidenCloudBot(cookie, i)
        
        success = bot.init()
        
        # 失败重试（回退到环境变量）
        if not success:
            bot.reset_to_env(cookie)
            success = bot.init()

        if success:
            msg = f"账号 {i + 1}: 登录成功，服务数: {len(bot.services)}"
            summary_msg += msg + "\n"
            for service in bot.services:
                bot.process_service(service)
        else:
            msg = f"账号 {i + 1}: 登录失败，请检查 Cookie"
            summary_msg += msg + "\n"
        
        print("\n----------------------------------------\n")
        if i < len(cookies_list) - 1:
            sleep_random(5000, 10000)

    if summary_msg:
        send_notify("HidenCloud 续期报告", summary_msg)
