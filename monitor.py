import requests
import time
import hmac
import hashlib
import base64
import os
from datetime import datetime
import pytz
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
    return timestamp, base64.b64encode(hmac_code).decode('utf-8')

def send_ding(content):
    """发送排版优化后的消息 - 支持更多标题加粗"""
    ts, sign = get_sign()
    url = f"{WEBHOOK}&timestamp={ts}&sign={sign}"
   
    # 标题加粗与格式优化（支持你提到的所有标题）
    titles = [
        "聊天总结", "具体信息", "选项信息", "经济事件",
        "个股/板块信息", "期权与仓位策略", "经济事件与宏观"
    ]
    
    for title in titles:
        content = content.replace(title, f"\n\n### **📌 {title}**\n")
    
    # 通用项目符号优化
    content = content.replace("•", "\n* ")
    
    data = {
        "msgtype": "markdown",
        "markdown": {
            "title": "财经摘要更新",
            "text": f"{content}\n\n---\n*🕒 监控时间(北京): {datetime.now(pytz.timezone('Asia/Shanghai')).strftime('%m-%d %H:%M')}*"
        }
    }
    requests.post(url, json=data)

def run():
    print(f"🌐 北京时间 {datetime.now(pytz.timezone('Asia/Shanghai')).strftime('%Y-%m-%d %H:%M')} 正在抓取网站内容...")
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
   
    try:
        res = requests.get(BASE_URL, headers=headers, timeout=20)
        res.encoding = 'utf-8'
        soup = BeautifulSoup(res.text, 'html.parser')
        main_body = soup.find('main') or soup.find('body')
        raw_text = main_body.get_text(separator="\n", strip=True)
       
        # 截取核心内容
        if "聊天总结" in raw_text:
            useful_content = raw_text[raw_text.find("聊天总结"):]
        else:
            useful_content = raw_text[:4000]  # 适当增加截取长度
        
        # 核心去重逻辑
        content_hash = hashlib.md5(useful_content.encode('utf-8')).hexdigest()
        hash_file = "last_content_hash.txt"
        last_hash = ""
        if os.path.exists(hash_file):
            with open(hash_file, "r") as f:
                last_hash = f.read().strip()
       
        if content_hash == last_hash:
            print("😴 内容没有更新，保持安静。")
            return
        
        # 执行推送
        send_ding(useful_content)
       
        # 记录新内容的指纹
        with open(hash_file, "w") as f:
            f.write(content_hash)
        print("🚀 检测到内容更新，已推送到钉钉！")
        
    except Exception as e:
        print(f"💥 运行异常: {str(e)}")

if __name__ == "__main__":
    run()
