# 程序功能：爬豆瓣电影上指定电影的短评
# 原创作者：马哥python说
import requests
from bs4 import BeautifulSoup
import pandas as pd
import os
import random
import time

# 请求头
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


def trans_star(v_str):
	"""转换评论星级"""
	v_str = v_str[0]
	if v_str == 'allstar10':
		return '1星'
	elif v_str == 'allstar20':
		return '2星'
	elif v_str == 'allstar30':
		return '3星'
	elif v_str == 'allstar40':
		return '4星'
	elif v_str == 'allstar50':
		return '5星'
	else:
		return '未知'


def get_short(v_movie_id):
	"""爬取短评数据"""
	seen = set()  # 去重集合：跨评论池判重，避免多池重复写入
	for pool_name, pool_param in pool_list:
		print('========== 开始爬取【{}】评论池 =========='.format(pool_name))
		for page in range(1, max_page + 1):  # 爬取前n页
			requests.packages.urllib3.disable_warnings()
			# 请求地址
			url = 'https://movie.douban.com/subject/{}/comments?start={}&limit=20&{}'.format(
				v_movie_id, (page - 1) * 20, pool_param)
			# 发送请求
			response = requests.get(url, headers=h1, verify=False)
			print(response.status_code)
			# 解析页面数据
			soup = BeautifulSoup(response.text, 'html.parser')
			# 所有评论数据
			reviews = soup.find_all('div', {'class': 'comment'})
			# 该池已到末尾（超出页数上限或返回异常页），直接换下一个池
			if not reviews:
				print('【{}】第{}页无数据，该评论池结束'.format(pool_name, page))
				break
			print('\n开始爬[{}]第{}页，共{}条评论'.format(pool_name, page, len(reviews)))
			time.sleep(random.uniform(1, 2))
			# 定义空列表用于存放数据
			user_name_list = []  # 评论者昵称
			star_list = []  # 评论星级
			time_list = []  # 评论时间
			ip_list = []  # 评论者ip属地
			vote_list = []  # 有用数
			content_list = []  # 评论内容
			for review in reviews:
				# 评论者昵称
				user_name = review.find('span', {'class': 'comment-info'}).find('a').text
				user_name_list.append(user_name)
				# 评论星级（加一层防御：个别评论池没有星级节点，避免索引越界）
				star_spans = review.find('span', {'class': 'comment-info'}).find_all('span')[1:2]
				star = trans_star(star_spans[0].get('class')) if star_spans else '未知'
				star_list.append(star)
				# 评论时间
				time2 = review.find(class_='comment-time').text.strip()
				print('评论时间：', time2)
				time_list.append(time2)
				# 评论者IP属地
				ip = review.find('span', {'class': 'comment-location'}).text
				ip_list.append(ip)
				# 有用数
				vote = review.find('span', {'class': 'votes vote-count'}).text
				vote_list.append(vote)
				# 评论内容
				content = review.find('span', {'class': 'short'}).text
				content = content.replace(',', '，').replace(' ', '').replace('\n', '').replace('\t', '').replace('\r', '')
				content_list.append(content)
			# 跨评论池去重：昵称+评论时间+评论内容 完全相同，视为同一条评论
			rows = []
			for row in zip(user_name_list, star_list, time_list, ip_list, vote_list, content_list):
				key = (row[0], row[2], row[5])
				if key in seen:
					continue
				seen.add(key)
				rows.append(row)
			if not rows:
				print('第{}页全部为重复数据，跳过保存'.format(page))
				continue
			df = pd.DataFrame(rows, columns=['评论者昵称', '评论星级', '评论时间', '评论者IP属地', '有用数', '评论内容'])
			df.insert(0, '页码', page)
			# 设置csv文件表头
			if os.path.exists(result_file):
				header = False
			else:
				header = True
			# 保存到csv文件
			df.to_csv(result_file, mode='a+', header=header, index=False, encoding='utf_8_sig')
			print('文件保存成功：', result_file)


if __name__ == '__main__':
	# 电影id
	movie_id = '1292052'
	# 最大爬取页（每个评论池独立分页，平台每个池最多20页/400条）
	max_page = 20  # 最大为20页
	# 评论池列表：多池循环+去重，单部电影采集量可达原来的数倍
	# 每个池独立分页、上限都是20页/400条；池之间用"昵称+时间+内容"去重，不会重复写入
	# 说明：'想看'池没有星级节点，其星级会记为"未知"；不需要可删掉该行
	pool_list = [
		('全部', 'status=P&sort=new_score'),
		('好评', 'percent_type=h&sort=new_score'),
		('中评', 'percent_type=m&sort=new_score'),
		('差评', 'percent_type=l&sort=new_score'),
		('想看', 'status=F&sort=new_score'),
	]
	# 保存文件名
	result_file = '豆瓣短评_{}_每池{}页.csv'.format(movie_id, max_page)
	# 如果csv文件存在，先删除之
	if os.path.exists(result_file):
		os.remove(result_file)
		print('结果文件存在，已删除: {}'.format(result_file))
	# 循环爬取短评
	get_short(movie_id)
