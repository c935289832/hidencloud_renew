# -*- coding: utf-8 -*-
"""
HidenCloud 自动续期 - Python 全日志推送版
"""
import os
import sys
import time
import json
import random
import requests
import cloudscraper # 必须保留，因为你已经用了 Cloudflare 绕过
from bs4 import BeautifulSoup
from urllib.parse import urljoin

# ================= 配置常量 =================
RENEW_DAYS = 7  # 根据你截图里是7天，这里改成了7
CACHE_FILE_NAME = 'hiden_cookies.json'
LOCAL_CACHE_PATH = os.path.join(os.path.dirname(__file__), CACHE_FILE_NAME)

# ================= 全局日志收集器 =================
ALL_LOGS = []

def log_print(msg):
    """
    既打印到控制台，也记录到内存供推送使用
    """
    print(msg)
    # 将日志加入全局列表
    ALL_LOGS.append(str(msg))

# ================= 消息推送模块 =================
def send_notify(text, desp):
    token = os.environ.get("WP_APP_TOKEN_ONE")
    uids_str = os.environ.get("WP_UIDs")
    
    if not token or not uids_str:
        log_print("⚠️ 未配置 WxPusher，跳过推送")
        return

    log_print(f"\n==== 开始推送通知: {text} ====\n")
    
    import re
    uids = [u.strip() for u in re.split(r'[,;\n]', uids_str) if u.strip()]
    
    url = 'https://wxpusher.zjiecode.com/api/send/message'
    data = {
        "appToken": token,
        # 将日志列表拼接成 HTML 格式，换行符转 <br>
        "content": f"<h3>{text}</h3><br><div style='font-size:14px;'>{desp.replace(chr(10), '<br>')}</div>",
        "summary": text, # 消息列表摘要
        "contentType": 2, # HTML
        "uids": uids
    }
    
    try:
        res = requests.post(url, json=data)
        if res.status_code == 200:
            print("✅ WxPusher 推送成功") # 这里用print不用log_print防止无限套娃
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
            log_print("⚠️ 未配置 WebDAV，跳过云端同步")
            return
            
        log_print("☁️ 正在从 Infinicloud 下载缓存...")
        try:
            res = requests.get(self.full_url, auth=(self.user, self.password), timeout=30)
            if res.status_code == 200:
                with open(LOCAL_CACHE_PATH, 'w', encoding='utf-8') as f:
                    f.write(res.text)
                log_print("✅ 云端缓存下载成功")
            elif res.status_code == 404:
                log_print("⚪ 云端暂无缓存文件 (首次运行)")
            else:
                log_print(f"⚠️ 下载失败，状态码: {res.status_code}")
        except Exception as e:
            log_print(f"❌ WebDAV 下载错误: {e}")

    def upload(self, data):
        if not self.url or not self.user:
            return
        
        log_print("☁️ 正在上传最新缓存到 Infinicloud...")
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
                log_print("✅ 云端缓存上传成功")
            else:
                log_print(f"❌ WebDAV 上传失败: {res.status_code}")
        except Exception as e:
            log_print(f"❌ WebDAV 上传错误: {e}")

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
                log_print("读取本地缓存失败")
        return {}

    @staticmethod
    def update(index, cookie_str):
        dav = WebDavManager()
        data = CacheManager.load()
        key = str(index)
        
        # 只要调用update就保存，确保最新
        if data.get(key) != cookie_str:
            data[key] = cookie_str
            with open(LOCAL_CACHE_PATH, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
            log_print(f"💾 [账号 {index + 1}] 本地缓存已更新")
            dav.upload(data)

# ================= 核心机器人类 =================
class HidenCloudBot:
    def __init__(self, env_cookie, index):
        self.index = index + 1
        self.base_url = "https://dash.hidencloud.com"
        
        # 使用 Cloudscraper
        self.session = cloudscraper.create_scraper(
            browser={
                'browser': 'chrome',
                'platform': 'windows',
                'desktop': True
            }
        )
        
        self.csrf_token = ""
        self.services = []
        
        # 加载 Cookie
        cached_data = CacheManager.load()
        cached_cookie = cached_data.get(str(index))
        
        if cached_cookie:
            log_print(f"[账号 {self.index}] 发现本地缓存 Cookie，优先使用...")
            self.load_cookie_str(cached_cookie)
        else:
            log_print(f"[账号 {self.index}] 使用环境变量 Cookie...")
            self.load_cookie_str(env_cookie)

    def log(self, msg):
        log_print(f"[账号 {self.index}] {msg}")

    def load_cookie_str(self, cookie_str):
        if not cookie_str:
            return
        cookie_dict = {}
        for item in cookie_str.split(';'):
            if '=' in item:
                k, v = item.split('=', 1)
                cookie_dict[k.strip()] = v.strip()
        self.session.cookies.update(cookie_dict)

    def get_cookie_str(self):
        return '; '.join([f"{c.name}={c.value}" for c in self.session.cookies])

    def save_current_cookies(self):
        CacheManager.update(self.index - 1, self.get_cookie_str())

    def reset_to_env(self, env_cookie):
        self.session.cookies.clear()
        self.load_cookie_str(env_cookie)
        self.log("切换回环境变量原始 Cookie 重试...")

    def request(self, method, url, data=None, headers=None):
        full_url = urljoin(self.base_url, url)
        try:
            resp = self.session.request(method, full_url, data=data, headers=headers, timeout=30)
            self.save_current_cookies()
            return resp
        except Exception as e:
            self.log(f"请求异常: {e}")
            raise

    def init(self):
        self.log("正在验证登录状态...")
        try:
            res = self.request('GET', '/dashboard')
            
            if '/login' in res.url:
                self.log("❌ 当前 Cookie 已失效")
                return False

            soup = BeautifulSoup(res.text, 'html.parser')
            log_print(f"👀 [调试] 网页标题是: {soup.title.string if soup.title else '无标题'}")

            token_tag = soup.find('meta', attrs={'name': 'csrf-token'})
            if token_tag:
                self.csrf_token = token_tag['content']

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
            # 1. 获取管理页面
            manage_res = self.request('GET', f"/service/{service['id']}/manage")
            soup = BeautifulSoup(manage_res.text, 'html.parser')

            # ================== 新增：检测是否允许续期 ==================
            import re
            
            # 查找 onclick 属性中包含 showRenewAlert 的按钮
            renew_btn = soup.find('button', onclick=re.compile(r'showRenewAlert'))
            
            if renew_btn:
                onclick_val = renew_btn['onclick']
                # 正则提取参数: showRenewAlert(15, 1, true)
                # Group 1: 剩余天数, Group 2: 阈值, Group 3: 是否免费
                match = re.search(r'showRenewAlert\((\d+),\s*(\d+),\s*(true|false)\)', onclick_val)
                
                if match:
                    days_until = int(match.group(1))
                    threshold = int(match.group(2))
                    is_free = match.group(3) == 'true'

                    # 模拟网页 JS 逻辑判断
                    if days_until > threshold:
                        threshold_text = "1 day" if threshold == 1 else f"{threshold} days"
                        
                        if is_free:
                            msg = f"You can only renew your free service when there is less than {threshold_text} left before it expires. Your service expires in {days_until} days."
                        else:
                            msg = f"You can only renew your service when there is less than {threshold_text} left before it expires. Your service expires in {days_until} days."
                        
                        # 打印提示并跳过续期
                        self.log(f"⏳ 暂未到达续期时间: {msg}")
                        return # <--- 关键：直接结束当前函数，不执行后续 POST
            # ==========================================================

            # 如果没有被拦截，继续寻找 Form Token
            token_input = soup.find('input', attrs={'name': '_token'})
            
            if not token_input:
                self.log(f"❌ 无法找到续期 Token (可能是服务已到期或页面结构变更)")
                return

            form_token = token_input['value']
            self.log(f"提交续期 ({RENEW_DAYS}天)...")
            sleep_random(1000, 2000)

            payload = {'_token': form_token, 'days': RENEW_DAYS}
            headers = {
                'X-CSRF-TOKEN': self.csrf_token,
                'Referer': f"https://dash.hidencloud.com/service/{service['id']}/manage"
            }
            
            res = self.request('POST', f"/service/{service['id']}/renew", data=payload, headers=headers)

            if '/invoice/' in res.url:
                self.log("⚡️ 续期成功，前往支付")
                self.perform_pay_from_html(res.text, res.url)
            else:
                self.log("⚠️ 续期请求已发送，检查账单...")
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

        payload = {}
        for inp in target_form.find_all('input'):
            name = inp.get('name')
            value = inp.get('value', '')
            if name:
                payload[name] = value

        self.log("👉 提交支付...")
        try:
            headers = {'X-CSRF-TOKEN': self.csrf_token, 'Referer': current_url}
            res = self.request('POST', target_action, data=payload, headers=headers)
            
            if res.status_code == 200:
                self.log("✅ 支付成功！")
            else:
                self.log(f"⚠️ 支付响应: {res.status_code}")
        except Exception as e:
            self.log(f"❌ 支付失败: {e}")

# ================= 主程序 =================
if __name__ == '__main__':
    env_cookies = os.environ.get("HIDEN_COOKIE", "")
    import re
    cookies_list = re.split(r'[&\n]', env_cookies)
    cookies_list = [c for c in cookies_list if c.strip()]

    if not cookies_list:
        log_print("❌ 未配置环境变量 HIDEN_COOKIE")
        sys.exit(0)

    WebDavManager().download()

    log_print(f"\n=== HidenCloud 续期脚本启动 (Python版) ===")

    for i, cookie in enumerate(cookies_list):
        bot = HidenCloudBot(cookie, i)
        success = bot.init()
        
        if not success:
            bot.reset_to_env(cookie)
            success = bot.init()

        if success:
            for service in bot.services:
                bot.process_service(service)
        else:
            log_print(f"账号 {i + 1}: 登录失败，请检查 Cookie")
        
        log_print("\n----------------------------------------\n")
        if i < len(cookies_list) - 1:
            sleep_random(5000, 10000)

    # 推送所有日志
    # 将日志数组合并成一个字符串
    final_content = "\n".join(ALL_LOGS)
    if final_content:
        send_notify("HidenCloud 续期报告", final_content)
