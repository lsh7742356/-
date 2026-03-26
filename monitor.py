import requests
import time
import hmac
import hashlib
import base64
import os
import re
from bs4 import BeautifulSoup

WEBHOOK = os.environ.get("DINGTALK_WEBHOOK")
SECRET = os.environ.get("DINGTALK_SECRET")
BASE_URL = "https://stock.autoin.me"

def get_sign():
    timestamp = str(round(time.time() * 1000))
    secret_enc = SECRET.encode('utf-8')
    string_to_sign = '{}\n{}'.format(timestamp, SECRET)
    hmac_code = hmac.new(secret_enc, string_to_sign.encode('utf-8'), digestmod=hashlib.sha256).digest()
    sign = base64.b64encode(hmac_code).decode('utf-8')
    return timestamp, sign

def send_ding(title, content):
    ts, sign = get_sign()
    url = f"{WEBHOOK}&timestamp={ts}&sign={sign}"
    if len(content) > 3500:
        content = content[:3500] + "\n\n...(内容过长)..."
    data = {
        "msgtype": "markdown",
        "markdown": {
            "title": "策略更新",
            "text": f"# {title}\n\n{content}\n\n---\n*推送时间: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())}*"
        }
    }
    requests.post(url, json=data)

def run():
    print("🌐 开始全量扫描页面链接...")
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)'}
        res = requests.get(BASE_URL, headers=headers, timeout=20)
        res.encoding = 'utf-8'
        soup = BeautifulSoup(res.text, 'html.parser')
        
        # 寻找所有包含日期格式（如 03-26 或 23:01）的链接
        all_links = soup.find_all('a', href=True)
        target_link = None
        
        for link in all_links:
            href = link['href']
            text = link.get_text(strip=True)
            # 只要链接包含 summaries 且文字里有数字（时间），就是我们要的
            if '/summaries/' in href and any(char.isdigit() for char in text):
                # 排除掉纯“历史总结”字样的链接
                if "历史总结" not in text:
                    target_link = link
                    break
        
        if not target_link:
            print("❌ 依然找不到时间轴链接，尝试直接抓取页面第一个 summary 链接")
            target_link = soup.find('a', href=lambda x: x and '/summaries/' in x)

        if not target_link:
            print("💥 网页上没有任何有效链接，请检查网址是否正确。")
            return

        detail_url = BASE_URL + target_link['href']
        title = target_link.get_text(strip=True)
        print(f"✅ 锁定目标: {title} -> {detail_url}")

        # 检查重复
        last_url = ""
        if os.path.exists("last_url.txt"):
            with open("last_url.txt", "r") as f: last_url = f.read().strip()
        if detail_url == last_url:
            print("😴 该内容已推送，无需重复。")
            return

        # 抓取正文
        detail_res = requests.get(detail_url, headers=headers, timeout=20)
        detail_res.encoding = 'utf-8'
        detail_soup = BeautifulSoup(detail_res.text, 'html.parser')
        
        # 抓取所有加粗文字或段落，这些通常是总结重点
        content_lines = []
        main_box = detail_soup.find('main') or detail_soup.body
        for tag in main_box.find_all(['h2', 'h3', 'p', 'li', 'strong']):
            txt = tag.get_text(strip=True)
            if txt and len(txt) > 5 and not any(x in txt for x in ["历史总结", "指数", "本页"]):
                content_lines.append(f"* {txt}" if tag.name == 'li' else txt)

        full_content = "\n\n".join(content_lines)
        send_ding(title, full_content or "抓取成功但正文为空，请点击链接查看。")
        
        with open("last_url.txt", "w") as f: f.write(detail_url)
        print("🚀 钉钉推送指令已发出！")

    except Exception as e:
        print(f"💥 发生错误: {e}")

if __name__ == "__main__":
    run()
