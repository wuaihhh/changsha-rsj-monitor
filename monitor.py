import requests
from bs4 import BeautifulSoup
import os
import json

# --- 监控配置列表 ---
# 以后想增加网站，只需按格式在下面添加一组 {} 即可
MONITOR_TASKS = [
    {
        "name": "湖南省人社厅-事业单位招聘",
        "url": "https://rst.hunan.gov.cn/rst/xxgk/zpzl/sydwzp/index.html",
        "selector": ".news_list li", # 湖南省厅通常的列表结构
        "base_url": "https://rst.hunan.gov.cn"
    },
    {
        "name": "长沙市人社局-事业单位招聘",
        "url": "http://rsj.changsha.gov.cn/rszc/rsrc_131369/gkzk_131379/sydwzk_131381/",
        "selector": ".list li", # 长沙市局通常的列表结构
        "base_url": "http://rsj.changsha.gov.cn"
    }
]

SCKEY = os.environ.get('SCKEY')
HISTORY_FILE = "history.json"

def get_latest_info(task):
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        response = requests.get(task['url'], timeout=30, headers=headers)
        response.encoding = 'utf-8'
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 根据选择器获取第一条公告
        first_item = soup.select_one(task['selector'])
        if not first_item:
            return None, None
            
        a_tag = first_item.find('a')
        title = a_tag.get_text(strip=True)
        link = a_tag['href']
        
        # 处理相对路径链接
        if link.startswith('.'):
            # 简单处理 ./info.html 这种格式
            link = task['url'][:task['url'].rfind('/')+1] + link.lstrip('./')
        elif link.startswith('/'):
            link = task['base_url'] + link
            
        return title, link
    except Exception as e:
        print(f"检查网站 [{task['name']}] 出错: {e}")
        return None, None

def send_wechat(msg_list):
    if not msg_list:
        return
    
    content = "\n\n".join(msg_list)
    send_url = f"https://sctapi.ftqq.com/{SCKEY}.send"
    data = {
        "title": "发现招聘信息更新！",
        "desp": content
    }
    requests.post(send_url, data=data)

if __name__ == "__main__":
    # 加载历史记录
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            history = json.load(f)
    else:
        history = {}

    updates = []
    
    for task in MONITOR_TASKS:
        name = task['name']
        current_title, current_link = get_latest_info(task)
        
        if current_title:
            # 如果是第一次监控或标题发生了变化
            if name not in history or history[name] != current_title:
                print(f"[{name}] 发现更新: {current_title}")
                updates.append(f"### {name}\n【标题】：{current_title}\n\n[点击查看详情]({current_link})")
                history[name] = current_title
            else:
                print(f"[{name}] 无更新")
    
    # 如果有更新，发送微信并保存历史
    if updates:
        send_wechat(updates)
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(history, f, ensure_ascii=False, indent=4)
