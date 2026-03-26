import requests
import time
import hmac
import hashlib
import base64
import os
import re
from bs4 import BeautifulSoup

# 配置信息（请确保 GitHub Secrets 已设置）
WEBHOOK = os.environ.get("DINGTALK_WEBHOOK")
SECRET = os.environ.get("DINGTALK_SECRET")
BASE_URL = "https://stock.autoin.me"

def get_sign():
    """钉钉安全加签"""
    timestamp = str(round(time.time() * 1000))
    secret_enc = SECRET.encode('utf-8')
    string_to_sign = '{}\n{}'.format(timestamp, SECRET)
    hmac_code = hmac.new(secret_enc, string_to_sign.encode('utf-8'), digestmod=hashlib.sha256).digest()
    sign = base64.b64encode(hmac_code).decode('utf-8')
    return timestamp, sign

def send_ding(content):
    """发送格式化后的内容"""
    ts, sign = get_sign()
    url = f"{WEBHOOK}&timestamp={ts}&sign={sign}"
    
    # 简单的排版优化：给大标题加点料
    content = content.replace("聊天总结", "## 📝 聊天总结")
    content = content.replace("具体信息", "### 🔍 具体信息")
    content = content.replace("选项信息", "### 📊 选项信息")
    content = content.replace("经济事件", "### 📅 经济事件")

    full_markdown = f"{content}\n\n---\n*推送时间: {time.strftime('%Y-%m-%d %H:%M:%S')}*"
    
    # 钉钉长度限制保护
    if len(full_markdown) > 5000:
        full_markdown = full_markdown[:5000] + "\n\n...(内容过长，已截断)..."

    data = {
        "msgtype": "markdown",
        "markdown": {"title": "财经摘要更新", "text": full_markdown}
    }
    requests.post(url, json=data)

def run():
    print("🌐 正在读取首页实时内容...")
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    }
    
    try:
        # 1. 直接请求首页（就像你手动打开浏览器一样）
        res = requests.get(BASE_URL, headers=headers, timeout=20)
        res.encoding = 'utf-8'
        
        # 2. 解析网页，提取所有文字
        soup = BeautifulSoup(res.text, 'html.parser')
        
        # 直接拿正文容器，通常是 main 或者 body
        main_body = soup.find('main') or soup.find('body')
        raw_text = main_body.get_text(separator="\n", strip=True)
        
        # 3. 截取核心部分：从“聊天总结”开始，过滤掉顶部的菜单导航
        if "聊天总结" in raw_text:
            useful_content = raw_text[raw_text.find("聊天总结"):]
        else:
            # 如果没找到关键字，可能页面还没加载完，取前3000字兜底
            useful_content = raw_text[:3000]

        # 4. 内容去重逻辑（基于文字内容的哈希值）
        content_hash = hashlib.md5(useful_content.encode('utf-8')).hexdigest()
        last_hash = ""
        if os.path.exists("last_content_hash.txt"):
            with open("last_content_hash.txt", "r") as f:
                last_hash = f.read().strip()
        
        if content_hash == last_hash:
            print("😴 首页内容未发生变化，无需推送。")
            return

        # 5. 执行推送
        print("🚀 发现新干货，正在推送到钉钉...")
        send_ding(useful_content)
        
        # 记录本次内容的指纹
        with open("last_content_hash.txt", "w") as f:
            f.write(content_hash)
        print("✅ 任务完成！")

    except Exception as e:
        print(f"💥 运行异常: {str(e)}")

if __name__ == "__main__":
    run()
