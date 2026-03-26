import requests
import time
import hmac
import hashlib
import base64
import os
from bs4 import BeautifulSoup

# 配置信息
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
    
    # 钉钉内容长度限制处理
    if len(content) > 4000:
        content = content[:4000] + "\n\n...(内容过长，仅截取部分)..."

    data = {
        "msgtype": "markdown",
        "markdown": {
            "title": "策略更新",
            "text": f"# {title}\n\n{content}\n\n---\n*推送时间: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())}*"
        }
    }
    requests.post(url, json=data)

def run():
    print("🌐 正在扫描侧边栏最新时间点...")
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'}
        res = requests.get(BASE_URL, headers=headers, timeout=20)
        res.encoding = 'utf-8'
        soup = BeautifulSoup(res.text, 'html.parser')
        
        # --- 核心改动：寻找侧边栏第一个具体的时间总结链接 ---
        # 排除掉“首页”、“历史总结”等大标题，精准找包含具体日期的链接
        sidebar_links = soup.find_all('a', href=lambda x: x and '/summaries/' in x)
        
        target_node = None
        for link in sidebar_links:
            text = link.get_text(strip=True)
            # 匹配包含类似 "2026-03-26" 日期格式的链接
            if "202" in text and ":" in text:
                target_node = link
                break
        
        if not target_node:
            print("⚠️ 未能在时间轴找到具体的时间总结链接")
            return

        detail_url = BASE_URL + target_node['href']
        title = target_node.get_text(strip=True)
        print(f"🔍 锁定最新时间轴: {title} -> {detail_url}")

        # 检查重复
        last_url = ""
        if os.path.exists("last_url.txt"):
            with open("last_url.txt", "r") as f:
                last_url = f.read().strip()
        if detail_url == last_url:
            print("😴 该时间段内容已推送过")
            return

        # 进入详情页抓取正文
        print("📖 正在提取正文总结...")
        detail_res = requests.get(detail_url, headers=headers, timeout=20)
        detail_res.encoding = 'utf-8'
        detail_soup = BeautifulSoup(detail_res.text, 'html.parser')
        
        # 提取逻辑：抓取页面中所有的总结条目
        content_lines = []
        # 排除侧边栏和导航，只在正文区找
        main_area = detail_soup.find('main') or detail_soup.body
        
        # 提取所有段落、标题和列表项
        for tag in main_area.find_all(['h1', 'h2', 'h3', 'p', 'li']):
            txt = tag.get_text(strip=True)
            if not txt or any(x in txt for x in ["历史总结", "指数", "本页", "具体信息"]):
                continue
            
            if tag.name.startswith('h'):
                content_lines.append(f"### {txt}")
            elif tag.name == 'li':
                content_lines.append(f"* {txt}")
            else:
                content_lines.append(txt)

        full_content = "\n\n".join(content_lines)
        
        if len(full_content) < 20:
            full_content = f"未能自动抓取到文字正文，请[点击链接手动查看]({detail_url})"

        send_ding(title, full_content)
        
        with open("last_url.txt", "w") as f:
            f.write(detail_url)
        print("✅ 任务完成，已推送最新时间段内容")

    except Exception as e:
        print(f"💥 运行错误: {e}")

if __name__ == "__main__":
    run()
