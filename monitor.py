import requests
from bs4 import BeautifulSoup
import os

# 配置目标网页和推送Key
URL = "http://rsj.changsha.gov.cn/xxgk/rsxx/sydwzp/"
SCKEY = os.environ.get('SCKEY')

def get_latest_news():
    try:
        # 发送请求获取内容
        response = requests.get(URL, timeout=20)
        response.encoding = 'utf-8'
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 定位公告列表（根据长沙人社局页面结构调整）
        # 通常是找到 class 为 "list-content" 或类似的 ul/li 标签
        news_list = soup.find('ul', class_='news_list') # 这是一个通用的推测，实际需根据页面微调
        if not news_list:
            # 备选方案：如果结构不同，尝试获取第一个li
            first_item = soup.select_one('.news_list li') or soup.select_one('.list li')
        else:
            first_item = news_list.find('li')
            
        title = first_item.find('a').get_text(strip=True)
        link = "http://rsj.changsha.gov.cn" + first_item.find('a')['href']
        return title, link
    except Exception as e:
        print(f"抓取失败: {e}")
        return None, None

def send_wechat(title, link):
    send_url = f"https://sctapi.ftqq.com/{SCKEY}.send"
    data = {
        "title": "长沙人社局新公告！",
        "desp": f"最新公告标题：{title}\n\n[点击查看详情]({link})"
    }
    requests.post(send_url, data=data)

if __name__ == "__main__":
    current_title, current_link = get_latest_news()
    
    if current_title:
        # 读取上次记录的标题进行对比
        history_file = "last_title.txt"
        last_title = ""
        if os.path.exists(history_file):
            with open(history_file, "r", encoding="utf-8") as f:
                last_title = f.read().strip()
        
        if current_title != last_title:
            print(f"发现更新：{current_title}")
            send_wechat(current_title, current_link)
            # 保存新标题
            with open(history_file, "w", encoding="utf-8") as f:
                f.write(current_title)
        else:
            print("没有新消息")
