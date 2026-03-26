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
    """钉钉加签逻辑"""
    timestamp = str(round(time.time() * 1000))
    secret_enc = SECRET.encode('utf-8')
    string_to_sign = '{}\n{}'.format(timestamp, SECRET)
    string_to_sign_enc = string_to_sign.encode('utf-8')
    hmac_code = hmac.new(secret_enc, string_to_sign_enc, digestmod=hashlib.sha256).digest()
    sign = base64.b64encode(hmac_code).decode('utf-8')
    return timestamp, sign

def send_ding(title, article_content):
    """发送长文本内容到钉钉"""
    ts, sign = get_sign()
    url = f"{WEBHOOK}&timestamp={ts}&sign={sign}"
    
    # 限制字数防止钉钉单条消息过长（最大支持约4000字）
    if len(article_content) > 3500:
        article_content = article_content[:3500] + "\n\n...(内容过长，仅显示部分)..."

    data = {
        "msgtype": "markdown",
        "markdown": {
            "title": title,
            "text": f"## 📢 {title}\n\n{article_content}\n\n---\n*推送时间: {time.strftime('%H:%M:%S', time.localtime())}*"
        }
    }
    
    res = requests.post(url, json=data)
    print(f"📡 钉钉推送结果: {res.text}")

def run():
    print("🌐 正在扫描主页...")
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get(BASE_URL, headers=headers, timeout=20)
        res.encoding = 'utf-8'
        soup = BeautifulSoup(res.text, 'html.parser')
        
        # 1. 寻找最新的详情页链接
        link_node = soup.find('a', href=lambda x: x and '/summaries/' in x)
        if not link_node:
            print("⚠️ 未找到新内容链接")
            return

        detail_url = BASE_URL + link_node['href']
        title = link_node.get_text(strip=True)
        print(f"🔍 发现详情页: {detail_url}")

        # 2. 检查是否已推送过
        last_url = ""
        if os.path.exists("last_url.txt"):
            with open("last_url.txt", "r") as f:
                last_url = f.read().strip()
        
        if detail_url == last_url:
            print("😴 内容已是最新，跳过。")
            return

        # 3. 核心步骤：进入详情页抓取正文文字
        print("📖 正在进入详情页提取文字...")
        detail_res = requests.get(detail_url, headers=headers, timeout=20)
        detail_res.encoding = 'utf-8'
        detail_soup = BeautifulSoup(detail_res.text, 'html.parser')
        
        content_parts = []
        # 寻找主要的文字区域
        main_content = detail_soup.find('main') or detail_soup.find('article') or detail_soup.find('body')
        
        if main_content:
            # 抓取标题、段落和列表内容
            for element in main_content.find_all(['h1', 'h2', 'h3', 'p', 'li']):
                text = element.get_text(strip=True)
                if text and "股票摘要" not in text and "历史总结" not in text:
                    # 给不同标签增加简单的 Markdown 样式
                    if element.name.startswith('h'):
                        content_parts.append(f"### {text}")
                    elif element.name == 'li':
                        content_parts.append(f"* {text}")
                    else:
                        content_parts.append(text)
        
        full_text = "\n\n".join(content_parts)
        
        if not full_text:
            full_text = "未能自动提取到正文，请手动查看详情。"

        # 4. 推送并记录
        send_ding(title, full_text)
        
        with open("last_url.txt", "w") as f:
            f.write(detail_url)
        print("✅ 全文推送成功")

    except Exception as e:
        print(f"💥 运行异常: {e}")

if __name__ == "__main__":
    run()
