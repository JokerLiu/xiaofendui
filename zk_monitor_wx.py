# -*- coding: utf-8 -*-
import json
import os
import re
import time
import logging
import itchat
import random
from pyquery import PyQuery as py
from datetime import datetime

# 日志格式设定
logging.basicConfig(level=logging.INFO, format='\n%(asctime)s - %(levelname)s: %(message)s')
# 存储目录
BASE_DIR = '/tmp'
# 临时文件
ZK_TMP_FILE = BASE_DIR + '/zk_monitor.json'
# 请求头
REQUEST_HEADERS = {
	'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/53.0.2785.143 Safari/537.36'
}
# 爬虫链接
ZK_BASE_URL = 'http://www.zuanke8.com/forum.php?mod=forumdisplay&fid=15&filter=author&orderby=dateline'
ZK_POST_URL = 'http://www.zuanke8.com/thread-%s-1-1.html'
# 任务间隔时间
ZK_TASK_INTERVAL = 30
# 编码
UTF8_ENCODING = 'utf-8'
GBK_ENCODING = 'gbk'
# 监控关键字
KEYWORD = {
    'include': '密令|红包|洪水|大水|有水|速度|神券|京豆',
    'exclude': '权限|水贴'
}
# 匹配群聊名称
MATCH_ROOMS = ['双11小分队']
# 全局存储数据
result = dict()
last_result = dict()
# 推送名单
user_names = list()


def main_handler(event, context):
    global result, last_result
    try:
        logging.info('临时文件：' + ZK_TMP_FILE)
        if not os.path.exists(ZK_TMP_FILE):
            logging.info('临时文件不存在')
        else:
            with open(ZK_TMP_FILE, 'r', encoding=UTF8_ENCODING) as f:
                result = json.load(f)
        logging.info('当前存储数据量：' + str(len(result.keys())))

        # 首页热门内容
        d = py(ZK_BASE_URL, headers=REQUEST_HEADERS, encoding=GBK_ENCODING)
        # 每个帖子
        d('#threadlisttableid tbody').each(deal_post)
        return "Success"
    except Exception as ex:
        logging.error('主任务运行异常：' + str(ex))
        raise ex
    finally:
        # 创建存储目录
        if not os.path.exists(BASE_DIR):
            os.makedirs(BASE_DIR)
        # 存储结果
        with open(ZK_TMP_FILE, 'w', encoding=UTF8_ENCODING) as f:
            # 超过数量清空
            if len(result.keys()) > 1500:
                result.clear()
                result = last_result
            logging.info('保存数据结果')
            json.dump(result, f)
            last_result.clear()


# 每个帖子
def deal_post(i, e):
    global result, last_result
    match = re.match(r'normalthread_(\d+)', str(py(e).attr('id')))
    if match is None:
        return
    # 帖子主键
    post_id = match.group(1)
    # 已存在
    if result.get(post_id) is not None:
        return
    # 帖子标题
    title = py(e).find('th').text()
    if re.match(r'.*(' + KEYWORD['include'] + ').*', title, re.I) is None \
        or re.match(r'.*' + KEYWORD['exclude'] + '.*', title, re.I) is not None:
        return
    # 帖子地址
    # url = py(e).find('th a').attr('href')
    url = ZK_POST_URL % post_id
    # class="by"
    time_ele = py(e).find('td:eq(1)')
    content = get_post_content(url)
    info =  {
        'url': url, 
        'title': title, 
        'time': time_ele.find('em').text(), 
        'content': content
    }
    result[post_id] = info
    last_result[post_id] = info
    logging.info('准备推送信息：' +  str(result[post_id]))
    content = '%s\n\n%s\n\n电脑版：%s' % (result[post_id]['title'], result[post_id]['content'], result[post_id]['url'])
    # 推送用户名单
    global user_names
    for name in user_names:
        itchat.send_msg(content, toUserName=name)
        time.sleep(random.randint(2, 5))


# 帖子链接内容
def get_post_content(url):
    d = py(url, headers=REQUEST_HEADERS, encoding=GBK_ENCODING)
    div = d('#postlist>div:first')
    tr = div.find('tr:first')
    content = tr.find('.t_f').text()
    return content


if __name__ == '__main__':
    logging.info('请扫描二维码登录')
    itchat.auto_login(hotReload=True, enableCmdQR=True)
    logging.info('登录成功')
    chatrooms = itchat.get_chatrooms(contactOnly=True)
    global user_names
    for room in chatrooms:
        logging.info('获取群聊通讯：' + room['NickName'] + '|' + room['UserName'])
        if room['NickName'] in MATCH_ROOMS:
            user_names.append(room['UserName'])
    # 定时循环
    while True:
        try:
            main_handler(None, None)
        except Exception as ex:
            logging.error('主线程异常：' + str(ex))
        time.sleep(ZK_TASK_INTERVAL)
    # 退出登录
    itchat.logout()