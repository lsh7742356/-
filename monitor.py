import requests
import time
import hmac
import hashlib
import base64
import os
import re
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

def send_ding(content, beijing_time):
    """发送消息 - 温和美化标题，不破坏原结构"""
    ts, sign = get_sign()
    url = f"{WEBHOOK}&timestamp={ts}&sign={sign}"
   
    # 温和的标题加粗（只对主要标题做处理，避免混淆）
    # 保留网页原本的标题样式，只给重要标题加粗
    content = re.sub(r'^(#+\s*)(.+?)$', r'\1**📌 \2**', content, flags=re.MULTILINE)  # 处理 Markdown 标题
    content = re.sub(r'^(##\s*聊天总结)', r'### **📌 聊天总结**', content, flags=re.MULTILINE)
    content = re.sub(r'^(##\s*具体信息)', r'### **📌 具体信息**', content, flags=re.MULTILINE)
    content = re.sub(r'^(###\s*指数/点位信息)', r'#### **📌 指数/点位信息**', content, flags=re.MULTILINE)
    content = re.sub(r'^(###\s*个股/板块信息)', r'#### **📌 个股/板块信息**', content, flags=re.MULTILINE)
    content = re.sub(r'^(###\s*期权信息)', r'#### **📌 期权信息**', content, flags=re.MULTILINE)
    content = re.sub(r'^(###\s*经济事件与宏观)', r'#### **📌 经济事件与宏观**', content, flags=re.MULTILINE)
    
    # 项目符号优化
    content = content.replace("•", "\n* ")
    
    data = {
        "msgtype": "markdown",
        "markdown": {
            "title": "财经摘要更新",
            "text": f"{content}\n\n---\n*🕒 本次更新北京时间: {beijing_time}*"
        }
    }
    requests.post(url, json=data)

def extract_beijing_time(text):
    """提取北京时间（唯一去重标准）"""
    patterns = [
        r'北京时间[：:]\s*([\d\-:\sCST]+)',
        r'北京时间[:：]\s*([0-9\-:\s]+)',
        r'(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}\s*CST)'
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1).strip()
    return None

def run():
    bj_now = datetime.now(pytz.timezone('Asia/Shanghai')).strftime('%Y-%m-%d %H:%M')
    print(f"🌐 北京时间 {bj_now} 开始监测...")

    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
   
    try:
        res = requests.get(BASE_URL, headers=headers, timeout=20)
        res.encoding = 'utf-8'
        soup = BeautifulSoup(res.text, 'html.parser')
        main_body = soup.find('main') or soup.find('body')
        raw_text = main_body.get_text(separator="\n", strip=True)
        
        # 提取当前北京时间（唯一判断标准）
        current_time = extract_beijing_time(raw_text)
        if not current_time:
            current_time = bj_now + ":00"
        
        print(f"📍 当前页面北京时间: {current_time}")
        
        # === 去重：只看北京时间 ===
        time_file = "last_beijing_time.txt"
        last_time = ""
        if os.path.exists(time_file):
            with open(time_file, "r", encoding="utf-8") as f:
                last_time = f.read().strip()
        
        if current_time == last_time:
            print("😴 北京时间未变化 → 内容相同，不推送")
            return
        
        # 保留原始内容结构，只做轻度美化
        useful_content = raw_text
        
        # 执行推送
        send_ding(useful_content, current_time)
        
        # 保存新的北京时间
        with open(time_file, "w", encoding="utf-8") as f:
            f.write(current_time)
        
        print(f"🚀 北京时间已更新 → 内容推送成功！")
        
    except Exception as e:
        print(f"💥 运行异常: {str(e)}")

if __name__ == "__main__":
    run()
