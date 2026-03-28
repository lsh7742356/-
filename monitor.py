import requests
import re
import base64
import hmac
import hashlib
import os
from datetime import datetime
import pytz
from bs4 import BeautifulSoup

# 配置信息
WEBHOOK = os.environ.get("DINGTALK_WEBHOOK")
SECRET = os.environ.get("DINGTALK_SECRET")
BASE_URL = "https://stock.autoin.me"

def get_sign():
    timestamp = str(round(datetime.now().timestamp() * 1000))
    secret_enc = SECRET.encode('utf-8')
    string_to_sign = '{}\n{}'.format(timestamp, SECRET)
    hmac_code = hmac.new(secret_enc, string_to_sign.encode('utf-8'), digestmod=hashlib.sha256).digest()
    return timestamp, base64.b64encode(hmac_code).decode('utf-8')

def send_ding(content, beijing_time):
    """最终版：干净标题 + 清晰人物对话"""
    ts, sign = get_sign()
    url = f"{WEBHOOK}&timestamp={ts}&sign={sign}"
   
    # 1. 主标题处理（只加粗，不加图标）
    content = re.sub(r'^财经聊天总结.*休市总结.*$', r'\n\n**财经聊天总结 - 休市总结（非交易时段）**\n\n', content, flags=re.MULTILINE)
    
    # 2. 其他标题只加粗，不加 📌
    titles = ["聊天总结", "具体信息", "指数/ETF 信息", "个股信息", "个股/板块信息", 
              "期权信息", "经济事件与宏观", "宏观与地缘政治", "不同观点对比"]
    for title in titles:
        content = content.replace(title, f'\n\n**{title}**\n\n')
    
    # 3. 人物对话统一处理（干净格式）
    # 管理员
    content = re.sub(r'(管理员\s*xiaozhaolucky[^：:]*[：:])', r'\n\n**👤 管理员 xiaozhaolucky**：', content)
    # 用户
    content = re.sub(r'(用户\s*[\w]+[^：:]*[：:])', r'\n\n**👤 \1**', content)
    
    # 4. 项目符号优化 + 换行
    content = content.replace("•", "\n\n• ")
    
    # 清理多余空行
    content = re.sub(r'\n{3,}', '\n\n', content)
    
    data = {
        "msgtype": "markdown",
        "markdown": {
            "title": "财经摘要更新",
            "text": f"{content}\n\n---\n*🕒 本次更新北京时间: {beijing_time}*"
        }
    }
    requests.post(url, json=data)

def extract_beijing_time(text):
    patterns = [
        r'北京时间[：:]\s*([\d\-:\sCST]+)',
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
        
        current_time = extract_beijing_time(raw_text) or bj_now + ":00"
        print(f"📍 当前页面北京时间: {current_time}")
        
        print("🔧 当前为临时测试模式 → 每次都推送")
        
        send_ding(raw_text, current_time)
        print("🚀 已执行推送")
        
    except Exception as e:
        print(f"💥 运行异常: {str(e)}")

if __name__ == "__main__":
    run()
