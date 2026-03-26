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
    
    # 标题精简，正文排版优化
    full_text = f"## 📈 {title}\n\n{content}\n\n---\n*推送时间: {time.strftime('%Y-%m-%d %H:%M:%S')}*"
    
    data = {
        "msgtype": "markdown",
        "markdown": {"title": "策略总结更新", "text": full_text}
    }
    r = requests.post(url, json=data)
    print(f"钉钉发送状态: {r.text}")

def run():
    print("🌐 正在深度解析网页侧边栏...")
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        res = requests.get(BASE_URL, headers=headers, timeout=20)
        res.encoding = 'utf-8'
        soup = BeautifulSoup(res.text, 'html.parser')
        
        # 1. 精准寻找左侧时间轴链接
        # 规律：这些链接文字都包含 "2026-" 且 href 包含 "/summaries/"
        links = soup.find_all('a', href=True)
        target_link = None
        
        for l in links:
            text = l.get_text(strip=True)
            href = l['href']
            # 排除掉“历史总结”和“首页”，只要带日期的具体总结
            if "/summaries/" in href and any(char.isdigit() for char in text) and ":" in text:
                target_link = l
                break
        
        if not target_link:
            print("❌ 无法定位时间轴链接，可能侧边栏未加载。")
            return

        detail_url = BASE_URL + target_link['href']
        title = target_link.get_text(strip=True)
        print(f"✅ 定位到最新时间点: {title}")

        # 2. 检查记录
        last_url = ""
        if os.path.exists("last_url.txt"):
            with open("last_url.txt", "r") as f: last_url = f.read().strip()
        if detail_url == last_url:
            print("😴 该时间点已推送过，跳过。")
            return

        # 3. 进入详情页抓取真正的“聊天总结”
        print("📖 正在提取正文总结文字...")
        detail_res = requests.get(detail_url, headers=headers, timeout=20)
        detail_res.encoding = 'utf-8'
        detail_soup = BeautifulSoup(detail_res.text, 'html.parser')
        
        content_parts = []
        # 定位正文区域 (通常在 main 或 article 中)
        article = detail_soup.find('main') or detail_soup.find('article') or detail_soup.body
        
        # 寻找“聊天总结”标题之后的所有列表项和段落
        capture = False
        for tag in article.find_all(['h2', 'h3', 'p', 'li']):
            txt = tag.get_text(strip=True)
            if not txt: continue
            
            # 开始触发关键词
            if "总结" in txt or "具体信息" in txt:
                capture = True
                content_parts.append(f"### {txt}")
                continue
            
            if capture:
                # 排除掉干扰文字
                if any(x in txt for x in ["历史总结", "指数", "本页"]): continue
                
                if tag.name == 'li':
                    content_parts.append(f"* {txt}")
                else:
                    content_parts.append(txt)

        final_content = "\n\n".join(content_parts)
        
        if len(final_content) < 30:
            # 如果抓取失败，保留链接作为兜底
            final_content = f"内容提取失败，请[点击原文链接查看]({detail_url})"

        send_ding(title, final_content)
        
        with open("last_url.txt", "w") as f: f.write(detail_url)
        print("🚀 推送任务已完成")

    except Exception as e:
        print(f"💥 出错: {e}")

if __name__ == "__main__":
    run()
