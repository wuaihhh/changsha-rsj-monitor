# changsha-rsj-monitor
针对您需要同时监控多个网站（湖南省人社厅和长沙市人社局），并且未来还需要不断增加新网站的需求，我们需要将之前的脚本升级为**“多目标监控版本”**。

这种方案会将所有监控网站的信息放在一个配置列表里，循环执行。

### 1. 更新 `monitor.py` 脚本

请在您的 GitHub 仓库中，将 `monitor.py` 的内容替换为以下代码。这个版本支持配置多个目标，并能根据不同网站的特点使用不同的“提取规则”。

```python
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

```

### 2. 更新 `main.yml` (GitHub Actions 配置)

由于我们现在使用 `history.json` 来保存记录，所以需要修改 `main.yml` 中的文件提交部分：

在 `main.yml` 的最后一部分 `Commit changes` 修改如下：

```yaml
      - name: Commit changes
        run: |
          git config --local user.email "actions@github.com"
          git config --local user.name "GitHub Actions"
          # 注意这里改为添加 history.json
          git add history.json
          git commit -m "Update history" || exit 0
          git push

```

### 3. 如何增加新的监控网站？

以后如果您看到新的网站（比如：湘潭人社局、某个具体的大学招聘页），您不需要修改任何逻辑，只需要修改 `monitor.py` 里的 `MONITOR_TASKS` 列表：

1. 打开 `monitor.py` 的编辑页面。
2. 在 `MONITOR_TASKS` 列表末尾添加一个“花括号”组，例如：
```python
{
    "name": "某某市人社局",
    "url": "http://example.com/zp.html",
    "selector": ".list-item",  # 这里需要观察新网页的 HTML 结构，找到公告标题所在的标签类名
    "base_url": "http://example.com"
},

```


3. 保存（Commit）。GitHub Actions 会在下一次运行时自动开始监控这个新网站。

### 4. 关键点提示：关于 `selector`

不同政府网站的 HTML 结构不一样，所以 `selector`（选择器）是成败的关键：

* **省人社厅：** 结构通常比较整齐，`.news_list li` 往往能精准定位。
* **长沙市局：** 刚才给您的链接中，通常使用 `.list li` 或者 `.news-list-li`。
* **如何找？** 在电脑浏览器打开目标网页 -> 按 `F12` -> 点击左上角的小箭头 -> 点击网页里的公告标题。看它上面的父节点是什么标签（比如 `<li class="abc">`，那选择器就是 `.abc`）。

### 5. 常见问题排查

* **如果没有收到推送：** 手动运行一次 Action，查看运行日志。如果显示“检查网站...出错”，通常是 `selector` 没找对，或者网站有反爬虫机制（不过湖南这两个政府网站目前限制较少）。
* **重复收到通知：** 确认 `history.json` 是否成功提交回了 GitHub 仓库。如果没有这个文件，脚本每次运行都会认为是第一次运行。

这种方案不仅解决了您目前的两个网站，也为您未来建立自己的“招聘信息监控阵列”打下了基础。
