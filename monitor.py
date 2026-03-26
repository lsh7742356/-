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
    timestamp = str(round(time.time() * 1000))
    secret_enc = SECRET.encode('utf-8')
    string_to_sign = '{}\n{}'.format(timestamp, SECRET)
    string_to_sign_enc = string_to_sign.encode('utf-8')
    hmac_code = hmac.new(secret_enc, string_to_sign_enc, digestmod=hashlib.sha256).digest()
    sign = base64.b64encode(hmac_code).decode('utf-8')
    return timestamp, sign

def send_ding(title, article_content):
    ts, sign = get_sign()
    url = f"{WEBHOOK}&timestamp={ts}&sign={sign}"
    
    if len(article_content) > 3500:
        article_content = article_content[:3500] + "\n\n...(内容过长)..."

    data = {
        "msgtype": "markdown",
        "markdown": {
            "title": title,
            "text": f"## 📢 {title}\n\n{article_content}\n\n---\n*推送时间: {time.strftime('%H:%M:%S', time.localtime())}*"
        }
    }
    requests.post(url, json=data)

def run():
    print("🌐 扫描主页...")
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
        res = requests.get(BASE_URL, headers=headers, timeout=20)
        res.encoding = 'utf-8'
        soup = BeautifulSoup(res.text, 'html.parser')
        
        link_node = soup.find('a', href=lambda x: x and '/summaries/' in x)
        if not link_node: return

        detail_url = BASE_URL + link_node['href']
        title = link_node.get_text(strip=True)
        
        # 检查是否已发送
        last_url = ""
        if os.path.exists("last_url.txt"):
            with open("last_url.txt", "r") as f:
                last_url = f.read().strip()
        if detail_url == last_url: return

        print(f"📖 正在进入详情页提取: {detail_url}")
        detail_res = requests.get(detail_url, headers=headers, timeout=20)
        detail_res.encoding = 'utf-8'
        detail_soup = BeautifulSoup(detail_res.text, 'html.parser')
        
        # --- 暴力抓取逻辑升级 ---
        # 排除掉不需要的干扰区块
        for unwanted in detail_soup(['nav', 'footer', 'script', 'style', 'header']):
            unwanted.decompose()

        # 尝试寻找 Next.js 或常规文章的主要容器
        main_box = detail_soup.find('main') or detail_soup.find('article') or detail_soup.find('div', class_='content') or detail_soup.body
        
        lines = []
        if main_box:
            # 抓取所有包含文字的标签
            for tag in main_box.find_all(['h1', 'h2', 'h3', 'p', 'li', 'div'], recursive=True):
                # 只处理直接包含文字的标签，避免重复抓取父容器文字
                if tag.name in ['h1', 'h2', 'h3', 'p', 'li'] or (tag.name == 'div' and not tag.find(['p', 'div'])):
                    text = tag.get_text(strip=True)
                    if text and len(text) > 2: # 过滤掉太短的无意义字符
                        if tag.name.startswith('h'):
                            lines.append(f"### {text}")
                        elif tag.name == 'li':
                            lines.append(f"* {text}")
                        else:
                            lines.append(text)

        # 去重并合并
        full_text = ""
        seen = set()
        for line in lines:
            if line not in seen:
                full_text += line + "\n\n"
                seen.add(line)

        if not full_text.strip():
            full_text = f"抓取正文失败，请[点击链接查看原文]({detail_url})"

        send_ding(title, full_text)
        
        with open("last_url.txt", "w") as f:
            f.write(detail_url)
        print("✅ 推送完成")

    except Exception as e:
        print(f"💥 出错: {e}")

if __name__ == "__main__":
    run()
