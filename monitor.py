import requests
from bs4 import BeautifulSoup
import os
import json
import time
import warnings  # 新增：用于屏蔽警告

# --- 核心修复1：屏蔽 urllib3 的 InsecureRequestWarning 不安全请求警告 ---
warnings.filterwarnings('ignore', category=requests.packages.urllib3.exceptions.InsecureRequestWarning)

# --- 监控配置列表 ---
# 以后想增加网站，只需按格式在下面添加一组 {} 即可
MONITOR_TASKS = [
    {
        "name": "湖南省人社厅-事业单位招聘",
        "url": "https://rst.hunan.gov.cn/rst/xxgk/zpzl/sydwzp/index.html",
        "selector": ".news_list li",
        "base_url": "https://rst.hunan.gov.cn"
    },
    {
        "name": "长沙市人社局-事业单位招聘",
        "url": "http://rsj.changsha.gov.cn/rszc/rsrc_131369/gkzk_131379/sydwzk_131381/",
        "selector": ".list li",
        "base_url": "http://rsj.changsha.gov.cn"
    }
]

SCKEY = os.environ.get('SCKEY')
HISTORY_FILE = "history.json"

def get_latest_info(task):
    # 尝试 3 次重试
    for i in range(3):
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
                'Accept-Language': 'zh-CN,zh;q=0.9',  # 新增：模拟浏览器，降低被反爬概率
                'Connection': 'keep-alive'
            }
            # 保持 verify=False （跳过证书校验），解决政府网站证书不规范问题
            response = requests.get(task['url'], timeout=60, headers=headers, verify=False) 
            response.encoding = 'utf-8'
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                first_item = soup.select_one(task['selector'])
                if not first_item:
                    return None, None
                a_tag = first_item.find('a')
                if not a_tag:  # 新增：防止没有a标签导致报错
                    return None, None
                    
                title = a_tag.get_text(strip=True)
                link = a_tag['href'].strip()
                
                # --- 核心修复2：严谨的链接拼接逻辑（修复原逻辑缺陷）---
                if link.startswith('http://') or link.startswith('https://'):
                    # 完整链接，直接使用
                    full_link = link
                elif link.startswith('/'):
                    # 根路径，拼接base_url
                    full_link = task['base_url'].rstrip('/') + link
                else:
                    # 相对路径，拼接当前页面的URL
                    full_link = task['url'].rstrip('/') + '/' + link.lstrip('./')

                return title, full_link
            
        except Exception as e:
            print(f"第 {i+1} 次尝试访问 [{task['name']}] 失败: {str(e)}")
            time.sleep(10) # 等待 10 秒后重试
            
    return None, None

# --- 核心修复3：微信推送函数 完善超时+异常捕获+关闭SSL校验 ---
def send_wechat(msg_list):
    if not msg_list or not SCKEY:
        if not SCKEY:
            print("⚠️ 未配置SCKEY，无法推送微信消息")
        return
    
    content = "\n\n".join(msg_list)
    send_url = f"https://sctapi.ftqq.com/{SCKEY}.send"
    data = {
        "title": "发现招聘信息更新！",
        "desp": content
    }
    try:
        # 关键：添加 verify=False + timeout 防止推送卡死/失败
        res = requests.post(send_url, data=data, verify=False, timeout=30)
        if res.status_code == 200:
            print("✅ 微信推送成功！")
    except Exception as e:
        print(f"❌ 微信推送失败: {str(e)}")

if __name__ == "__main__":
    # 加载历史记录
    history = {}
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                history = json.load(f)
        except:
            print(f"⚠️ 历史文件 {HISTORY_FILE} 读取失败，将重新创建")
            history = {}

    updates = []
    print("="*50)
    print(f"开始监控招聘信息 | {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*50)
    
    for task in MONITOR_TASKS:
        name = task['name']
        current_title, current_link = get_latest_info(task)
        
        if current_title and current_link:
            # 如果是第一次监控或标题发生了变化
            if name not in history or history[name] != current_title:
                print(f"\n✅ [{name}] 发现更新！")
                print(f"标题：{current_title}")
                print(f"链接：{current_link}")
                updates.append(f"### {name}\n【标题】：{current_title}\n\n[点击查看详情]({current_link})")
                history[name] = current_title
            else:
                print(f"ℹ️ [{name}] 暂无更新")
        else:
            print(f"❌ [{name}] 未获取到有效招聘信息")
    
    # 如果有更新，发送微信并保存历史
    if updates:
        send_wechat(updates)
        # 保存历史记录
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(history, f, ensure_ascii=False, indent=4)
        print(f"\n✅ 历史记录已保存到 {HISTORY_FILE}")
    print("\n" + "="*50 + "\n监控完成\n")
