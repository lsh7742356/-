import requests
import time
import hmac
import hashlib
import base64
import os
import re
from bs4 import BeautifulSoup

# 配置信息（从 GitHub Secrets 读取）
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

def send_ding(title, content):
    """推送 Markdown 消息"""
    ts, sign = get_sign()
    url = f"{WEBHOOK}&timestamp={ts}&sign={sign}"
    
    # 限制长度防止钉钉拒绝接收
    if len(content) > 4000:
        content = content[:4000] + "\n\n...(内容过长，已截断)..."

    full_markdown = f"## 📍 {title}\n\n{content}\n\n---\n*推送时间: {time.strftime('%Y-%m-%d %H:%M:%S')}*"
    
    data = {
        "msgtype": "markdown",
        "markdown": {"title": "最新策略推送", "text": full_markdown}
    }
    r = requests.post(url, json=data)
    print(f"钉钉接口返回: {r.text}")

def run():
    print("🔍 开始地毯式搜索最新内容...")
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept-Language': 'zh-CN,zh;q=0.9',
        'Referer': BASE_URL
    }
    
    try:
        # 1. 抓取主页，定位左侧时间轴最新的那个链接
        res = requests.get(BASE_URL, headers=headers, timeout=20)
        res.encoding = 'utf-8'
        soup = BeautifulSoup(res.text, 'html.parser')
        
        # 寻找包含日期/时间格式且指向 summaries 的链接
        all_links = soup.find_all('a', href=True)
        target_link = None
        for l in all_links:
            href = l['href']
            text = l.get_text(strip=True)
            # 匹配 2026-03-26 这种格式，且排除掉“历史总结”大标题
            if "/summaries/" in href and ":" in text and "202" in text:
                target_link = l
                break
        
        if not target_link:
            print("❌ 无法定位时间轴链接，可能页面结构已变。")
            return

        detail_url = BASE_URL + target_link['href']
        title = target_link.get_text(strip=True)
        print(f"✅ 锁定目标页面: {title} ({detail_url})")

        # 2. 去重检查
        last_url = ""
        if os.path.exists("last_url.txt"):
            with open("last_url.txt", "r") as f: last_url = f.read().strip()
        if detail_url == last_url:
            print("😴 该内容已推送，无需重复执行。")
            return

        # 3. 抓取详情页源码
        detail_res = requests.get(detail_url, headers=headers, timeout=20)
        detail_res.encoding = 'utf-8'
        raw_html = detail_res.text
        
        # 4. 核心：地毯式提取关键词模块
        # 我们用正则把 HTML 标签全都换成换行，然后直接搜文字
        clean_text = re.sub(r'<[^>]+>', '\n', raw_html)
        
        modules = ["聊天总结", "具体信息", "选项信息", "经济事件"]
        final_parts = []
        
        for i, mod in enumerate(modules):
            if mod in clean_text:
                start_idx = clean_text.find(mod)
                # 截取该模块后 2000 字符
                chunk = clean_text[start_idx:start_idx+2000]
                
                # 尝试寻找下一个模块的开头来截断，保证不重叠
                next_mod_pos = 9999
                for other_mod in modules:
                    pos = chunk.find(other_mod, len(mod)) # 跳过当前的词
                    if pos != -1 and pos < next_mod_pos:
                        next_mod_pos = pos
                
                module_content = chunk[:next_mod_pos].strip()
                # 简单格式化：把模块名加粗
                module_content = module_content.replace(mod, f"### 📌 {mod}")
                final_parts.append(module_content)

        final_content = "\n\n---\n\n".join(final_parts)

        # 兜底：如果正则没抠出来，直接给链接
        if len(final_content) < 50:
            final_content = f"正文提取受限，请点击查看原文：[传送门]({detail_url})"

        # 5. 发送并保存记录
        send_ding(title, final_content)
        with open("last_url.txt", "w") as f: f.write(detail_url)
        print("🚀 推送任务圆满完成！")

    except Exception as e:
        print(f"💥 运行崩溃: {str(e)}")

if __name__ == "__main__":
    run()
