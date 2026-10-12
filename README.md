# 🎬 豆瓣短评爬虫 / Douban Short Comment Crawler

> 基于Python3的豆瓣电影短评数据采集爬虫，支持星级、IP属地、评论时间等核心字段

<p align="center">
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/Python-3.8+-blue.svg" alt="Python 3.8+"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-green.svg" alt="License: MIT"></a>
</p>

## 📖 项目简介

本项目是一款面向中文开发者的豆瓣电影短评采集源码，基于豆瓣电影短评页面开发。<img width="1440" height="835" alt="image" src="https://github.com/user-attachments/assets/d64f7b95-076c-46e6-bed2-65d1990cd6cb" />

源码具有以下特点：
- ✅ 源码简洁，逻辑清晰，易于理解
- ✅ 无需复杂依赖，仅需 requests + pandas
- ✅ **多评论池循环采集**，单部电影采集量最高可达单池的 5 倍
- ✅ **跨池自动去重**，多池数据不会重复写入
- ✅ 自动追加写入CSV，断点续传
- ✅ 支持评论星级转换
- ✅ 支持IP属地解析
- ✅ 内置随机延迟，防止频繁请求

## 📊 采集字段（7个核心字段）

| 字段 | 说明 | 示例 |
|------|------|------|
| 页码 | 当前页序号 | 1 |
| 评论者昵称 | 豆瓣用户昵称 | 某豆瓣用户 |
| 评论星级 | 评论星级（1-5星） | 4星 |
| 评论时间 | 标准时间格式 | 2026-04-26 |
| 评论者IP属地 | 评论者IP归属地 | 北京 |
| 有用数 | "有用"点赞数 | 128 |
| 评论内容 | 完整评论文本 | 非常不错的电影... |

采集结果图示：<img width="1365" height="797" alt="image" src="https://github.com/user-attachments/assets/4e6e4c26-b9e5-414a-a254-963e58933462" />


## 🚀 快速开始

### 环境要求

- Python 3.8+
- Windows / macOS / Linux

### 安装依赖

```bash
pip3 install requests pandas beautifulsoup4
```

### 基本使用

```bash
python3 douban_short_comment.py
```

> ⚠️ **运行前，仅需修改这三处**：电影ID `movie_id`、每个池的最大页数 `max_page`、评论池列表 `pool_list`。
> Cookie 在代码头部已预设示例值，如遇 403 请替换为自己的有效 Cookie。

### 演示视频
源码运行演示视频：[【Python爬虫实战】爬取豆瓣电影短评，以《热烈》为例](https://www.bilibili.com/video/BV1gh4y1v7VH/)

## 📈 采集量：为什么要用「多池」

豆瓣短评接口对**单个筛选条件下**的翻页有硬上限：**最多 20 页 / 400 条**（第 21 页返回 404）。
但同一个电影在不同筛选条件下的数据池是**互相独立**的，把多个池串起来采集，总量就能突破 400 条。

以《肖申克的救赎》(id=1292052) 实测为例，`max_page = 20`：

| 评论池 | 请求参数 | 采集行数 |
|--------|----------|----------|
| 全部 | `status=P` | 400 |
| 好评 | `percent_type=h` | 52 |
| 中评 | `percent_type=m` | 376 |
| 差评 | `percent_type=l` | 373 |
| 想看 | `status=F` | 399 |
| **合计（已去重）** | — | **1600** |

- 行数不足 400 的两个池，是因为**该池有相当一部分评论与「全部」池重叠，被自动去重丢弃**（好评池与全部池重叠度尤其高）。
- 相比旧版单池采集，同一部电影的数据量从 **400 条 → 1600 条**。
- `status=D`（在看）豆瓣返回 403，故未纳入。

## ⚙️ 核心原理

### 1. 请求地址

```
https://movie.douban.com/subject/{movie_id}/comments
```

### 2. 请求参数

| 参数 | 说明 |
|------|------|
| start | 起始位置（page-1）* 20 |
| limit | 每页评论数（固定20，传其他值也会被豆瓣忽略） |
| status | 评论池之一（`P` 看过；`F` 想看；`D` 在看，返回403） |
| percent_type | 评论池之一（`h` 好评 / `m` 中评 / `l` 差评 / 空 全部） |
| sort | 排序方式（new_score 最新排序） |

### 3. 请求头（需要携带Cookie）

```python
h1 = {
	'Cookie': '换成自己的cookie值',
	'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
	'Accept-Encoding': 'gzip, deflate',
	'Host': 'movie.douban.com',
	'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.4 Safari/605.1.15',
	'Accept-Language': 'zh-CN,zh-Hans;q=0.9',
	'Referer': 'https://movie.douban.com/subject/35267224/?from=showing',
	'Connection': 'keep-alive'
}
```

### 4. 核心代码逻辑

```python
def get_short(v_movie_id):
    seen = set()  # 去重集合：跨评论池判重
    for pool_name, pool_param in pool_list:      # ① 外层：遍历多个评论池
        for page in range(1, max_page + 1):      # ② 内层：每个池独立翻页
            url = 'https://movie.douban.com/subject/{}/comments?start={}&limit=20&{}'.format(
                v_movie_id, (page - 1) * 20, pool_param)
            response = requests.get(url, headers=h1, verify=False)
            soup = BeautifulSoup(response.text, 'html.parser')
            reviews = soup.find_all('div', {'class': 'comment'})
            if not reviews:      # 该池已到末尾，直接换下一个池
                break
            # 解析每个评论字段...
            # ③ 落盘前按 (昵称, 评论时间, 评论内容) 去重，重复的整页跳过
```

评论池配置（在 `__main__` 中修改即可）：

```python
pool_list = [
    ('全部', 'status=P&sort=new_score'),
    ('好评', 'percent_type=h&sort=new_score'),
    ('中评', 'percent_type=m&sort=new_score'),
    ('差评', 'percent_type=l&sort=new_score'),
    ('想看', 'status=F&sort=new_score'),
]
```

## 🔧 核心特性

### ⏱️ 请求间隔
内置随机延迟 `1-2秒`，避免频繁请求被封禁

### 🔄 自动追加写入
分页爬取时自动追加到CSV，避免数据丢失；如文件已存在会自动删除后重建

### 🔁 多池循环 + 跨池去重
外层循环遍历评论池、内层循环翻页，落盘前用 `(昵称, 评论时间, 评论内容)` 三元组判重。
注意：**「页码」是每个池内独立计数的**，所以 CSV 里页码会出现多次 1~20，可据此切分池段。

### ⭐ 星级自动转换
自动将CSS类名（如 `allstar40`）转换为直观的中文星级（4星）

### 🌐 IP属地解析
支持获取评论者的IP归属地（老评论可能没有该字段，为空属正常）

### 📝 内容清洗
自动过滤评论内容中的逗号、空格、换行符等，适配CSV格式

## ⚠️ 重要说明

### 🔑 关于Cookie

**必须携带有效Cookie才能爬取！** 请按照以下步骤获取：

1. 打开 Chrome 浏览器
2. 登录 [豆瓣电影](https://movie.douban.com)
3. 按 F12 打开开发者工具
4. 切换到 Network（网络）标签
5. 刷新页面，找到任意请求
6. 复制 Request Headers 中的 Cookie 值
7. 替换源码中的 `h1["Cookie"]`

> ⚠️ **重要**：Cookie必须在已登录状态下获取，否则会被重定向到 `sec.douban.com` 反爬页，取不到任何评论数据。

### 📄 页数限制

豆瓣对短评翻页有限制：**单个评论池最多只能爬取前20页**（每页20条，共400条），第21页返回404。
这是豆瓣的反爬机制，非本工具问题。**通过多池循环采集可突破单池400条的限制。**

### 🛡️ 注意事项

1. **频率控制**：已内置1-2秒随机延迟
2. **Cookie有效期**：豆瓣Cookie通常有时效，发现失效请重新获取
3. **页数上限**：每个评论池最多20页，超出部分无法爬取
4. **星级为空**：`想看`（`status=F`）池没有星级节点，该池的星级会记录为「未知」，属正常现象
5. **合规使用**：请遵守豆瓣服务条款，本工具仅供学习研究

## 📁 项目结构

```
爬豆瓣短评/
├── douban_short_comment.py            # 核心爬虫源码（多池+去重）
├── 豆瓣短评_1292052_每池20页.csv        # 演示数据：肖申克，5池共1600条
├── 豆瓣短评_35556001_前20页.csv         # 旧版单池演示数据：热烈，400条
├── 豆瓣短评爬虫-获取cookie方法.png      # Cookie获取教程截图
├── README.md                          # 项目说明
└── LICENSE                            # MIT协议
```

## 🎯 适用场景

- 📝 内容分析：舆情监控、热点追踪
- 📈 数据挖掘：社交网络分析、用户评论研究
- 🤖 机器学习：NLP训练数据集构建（情感分析）
- 📊 商业分析：电影口碑分析、竞品研究
- 🌐 IP分析：用户地域分布、评论来源分析

## 📜 开源协议

本项目采用 [MIT License](LICENSE)，可免费使用于个人和商业项目。

---

## 🔗 更多采集工具

作者 **@马哥python说** 还开发了多款数据采集软件，支持主流平台：

| 软件名称 | 平台 | 核心功能 |
|---------|------|---------|
| [爬小红书聚合软件](https://github.com/mashukui/xhs_one_spider) | 小红书 | 搜索评论采集、博主笔记采集、链接转换 |
| [爬微博聚合软件](https://github.com/mashukui/weibo_one_spider) | 微博 | 关键词搜索采集、博主主页采集、评论采集 |
| [爬抖音聚合软件](https://github.com/mashukui/douyin_one_spider) | 抖音 | 搜索评论采集、主页作品采集、链接转换 |
| [爬油管博主软件](https://github.com/mashukui/youtube_user) | YouTube | 博主搜索、智能筛选、16个核心字段 |
| [爬油管评论软件](https://github.com/mashukui/ytb_cmt_spider) | YouTube | 评论采集、10个关键字段 |
| [爬蒲公英软件](https://github.com/mashukui/pgy_spider) | 小红书KOL | 34个核心字段、智能筛选、媒介投放数据 |

---

📌 **声明**：本工具仅供学习研究使用，请勿用于商业牟利或任何违规场景。使用本工具产生的任何问题由使用者自行承担。

---

## 🔗 联系方式

- **原创作者**：马哥python说
- **公众号**：老男孩的平凡之路
<img width="1938" height="364" alt="二维码-公众号放底部v2" src="https://github.com/user-attachments/assets/bb4ad9ba-2230-432d-94ea-15ed236af201" />
