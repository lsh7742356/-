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
    """发送优化后的消息"""
    ts, sign = get_sign()
    url = f"{WEBHOOK}&timestamp={ts}&sign={sign}"
   
    # 标题加粗优化
    titles = [
        "聊天总结", "周末总结", "本周汇总", "休市总结", "群聊总结",
        "具体信息", "选项信息", "个股/板块信息", "个股信息", "板块信息",
        "期权与仓位策略", "期权策略", "仓位策略", 
        "经济事件", "经济事件与宏观", "宏观"
    ]
    
    for title in titles:
        content = content.replace(title, f"\n\n### **📌 {title}**\n")
    
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
    """提取页面中的北京时间（最核心判断依据）"""
    match = re.search(r'北京时间[：:]\s*([\d\-:\sCST]+)', text)
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
        
        # 提取当前页面的北京时间
        current_time = extract_beijing_time(raw_text)
        if not current_time:
            current_time = bj_now + ":00"   # 兜底
            print("⚠️ 未找到北京时间，使用当前运行时间")
        
        print(f"📍 当前页面北京时间: {current_time}")
        
        # === 去重核心：只对比北京时间 ===
        time_file = "last_beijing_time.txt"
        last_time = ""
        if os.path.exists(time_file):
            with open(time_file, "r", encoding="utf-8") as f:
                last_time = f.read().strip()
        
        if current_time == last_time:
            print("😴 北京时间未变化 → 内容相同，不推送")
            return
        
        # 提取核心内容（从聊天总结开始抓取）
        start_pos = -1
        start_keywords = ["聊天总结", "休市总结", "周末总结", "本周汇总", "群聊总结"]
        for kw in start_keywords:
            pos = raw_text.find(kw)
            if pos != -1:
                start_pos = pos
                break
        
        useful_content = raw_text[start_pos:] if start_pos != -1 else raw_text[:6000]
        
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
