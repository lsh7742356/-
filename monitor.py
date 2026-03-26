import requests
import time
import hmac
import hashlib
import base64
import os
import re

# 配置信息：确保你已经在 GitHub Secrets 中设置了 DINGTALK_WEBHOOK 和 DINGTALK_SECRET
WEBHOOK = os.environ.get("DINGTALK_WEBHOOK")
SECRET = os.environ.get("DINGTALK_SECRET")
BASE_URL = "https://stock.autoin.me"

def get_sign():
    """钉钉 HmacSHA256 加签认证"""
    timestamp = str(round(time.time() * 1000))
    secret_enc = SECRET.encode('utf-8')
    string_to_sign = '{}\n{}'.format(timestamp, SECRET)
    hmac_code = hmac.new(secret_enc, string_to_sign.encode('utf-8'), digestmod=hashlib.sha256).digest()
    sign = base64.b64encode(hmac_code).decode('utf-8')
    return timestamp, sign

def send_ding(title, content):
    """发送格式化后的 Markdown 消息"""
    ts, sign = get_sign()
    url = f"{WEBHOOK}&timestamp={ts}&sign={sign}"
    
    # 关键词美化排版
    for key in ["聊天总结", "具体信息", "选项信息", "经济事件"]:
        content = content.replace(key, f"\n\n--- \n### 📊 {key}\n")

    # 构造 Markdown 文本
    full_markdown = f"# {title}\n\n{content}\n\n---\n*更新于北京时间: {time.strftime('%Y-%m-%d %H:%M:%S')}*"
    
    # 钉钉消息长度限制处理
    if len(full_markdown) > 4000:
        full_markdown = full_markdown[:4000] + "\n\n**...内容过长，请访问官网查看完整版...**"

    data = {
        "msgtype": "markdown",
        "markdown": {"title": "财经策略实时推送", "text": full_markdown}
    }
    
    try:
        r = requests.post(url, json=data, timeout=10)
        print(f"钉钉推送状态: {r.text}")
    except Exception as e:
        print(f"推送失败: {e}")

def run():
    print("🚀 正在检索最新时间轴数据...")
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'application/json'
    }
    
    try:
        # 1. 获取首页数据索引，找到第一个（最新的）Slug
        # 这对应你截图左侧时间轴最顶部的蓝色链接
        index_api = f"{BASE_URL}/page-data/index/page-data.json"
        idx_res = requests.get(index_api, headers=headers, timeout=15)
        idx_res.raise_for_status()
        idx_data = idx_res.json()
        
        # 提取最新一条内容的路径标识 (Slug) 和标题
        latest_node = idx_data['result']['data']['allMarkdownRemark']['edges'][0]['node']
        slug = latest_node['fields']['slug']
        title = latest_node['frontmatter']['title']
        
        # 2. 检查去重记忆文件
        last_slug = ""
        if os.path.exists("last_url.txt"):
            with open("last_url.txt", "r") as f: last_slug = f.read().strip()
        
        if slug == last_slug:
            print(f"😴 当前内容 [{title}] 已推送过，无需操作。")
            return

        # 3. 直接请求该 Slug 对应的详细数据包 (page-data.json)
        # 这步操作相当于“点击”了链接并加载了全文
        print(f"📖 发现新内容，正在提取全文模块...")
        detail_api = f"{BASE_URL}/page-data{slug}page-data.json"
        detail_res = requests.get(detail_api, headers=headers, timeout=15)
        detail_data = detail_res.json()
        
        # 提取 HTML 源码
        raw_html = detail_data['result']['data']['markdownRemark']['html']
        
        # 4. 清理 HTML 标签并保留 Markdown 结构
        # 处理列表、换行，剔除所有 <> 标签
        content = re.sub(r'<li>', '\n* ', raw_html)
        content = re.sub(r'</?(p|div|h1|h2|h3|br|section|article)>', '\n', content)
        content = re.sub(r'<[^>]+>', '', content) # 剔除剩余标签
        
        # 压缩多余空行，保持排版紧凑
        final_text = "\n".join([line.strip() for line in content.split('\n') if line.strip()])

        # 5. 执行推送并更新记忆
        send_ding(title, final_text)
        
        with open("last_url.txt", "w") as f:
            f.write(slug)
        print(f"✅ 推送成功: {title}")

    except Exception as e:
        print(f"💥 抓取任务失败: {str(e)}")

if __name__ == "__main__":
    run()
