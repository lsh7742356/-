import requests
import time
import hmac
import hashlib
import base64
import os
from bs4 import BeautifulSoup

# 从 GitHub Secrets 读取环境变量
WEBHOOK = os.environ.get("DINGTALK_WEBHOOK")
SECRET = os.environ.get("DINGTALK_SECRET")
BASE_URL = "https://stock.autoin.me"

def get_sign():
    """生成钉钉安全设置所需的签名"""
    timestamp = str(round(time.time() * 1000))
    secret_enc = SECRET.encode('utf-8')
    string_to_sign = '{}\n{}'.format(timestamp, SECRET)
    string_to_sign_enc = string_to_sign.encode('utf-8')
    hmac_code = hmac.new(secret_enc, string_to_sign_enc, digestmod=hashlib.sha256).digest()
    sign = base64.b64encode(hmac_code).decode('utf-8')
    return timestamp, sign

def send_ding(title, link):
    """发送消息到钉钉"""
    ts, sign = get_sign()
    url = f"{WEBHOOK}&timestamp={ts}&sign={sign}"
    
    data = {
        "msgtype": "markdown",
        "markdown": {
            "title": "📊 策略更新提醒",
            "text": f"### 🚀 发现新策略总结\n\n**标题**: {title}\n\n**链接**: [点击阅读详情]({link})\n\n---\n*推送时间: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())}*"
        }
    }
    
    res = requests.post(url, json=data)
    print(f"📡 钉钉返回结果: {res.text}")

def run():
    print("🌐 开始抓取网页...")
    try:
        res = requests.get(BASE_URL, timeout=20)
        res.encoding = 'utf-8'
        soup = BeautifulSoup(res.text, 'html.parser')
        
        # 定位第一个包含 summaries 的链接
        link_node = soup.find('a', href=lambda x: x and '/summaries/' in x)
        
        if not link_node:
            print("⚠️ 未找到总结链接")
            return

        latest_url = BASE_URL + link_node['href']
        title_text = link_node.get_text(strip=True)
        print(f"🔍 找到链接: {latest_url}")

        # 读取记录防止重复
        last_url = ""
        if os.path.exists("last_url.txt"):
            with open("last_url.txt", "r") as f:
                last_url = f.read().strip()
        
        if latest_url != last_url:
            print("🚀 检测到更新，准备推送...")
            send_ding(title_text, latest_url)
            with open("last_url.txt", "w") as f:
                f.write(latest_url)
        else:
            print("😴 内容未更新")

    except Exception as e:
        print(f"💥 出错: {e}")

if __name__ == "__main__":
    run()
