# -*- coding: utf-8 -*-
import json
import os
import re
import time
import logging
import itchat
import random
import requests
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
TUAN_BASE_URL = 'http://www.0818tuan.com/list-1-0.html'
# 任务间隔时间
ZK_TASK_INTERVAL = 30
# 编码
UTF8_ENCODING = 'utf-8'
GBK_ENCODING = 'gbk'
GB2312_ENCODING = 'gb2312'
# 监控关键字
KEYWORD = {
    'include': r'密令|红包|洪水|大水|有水|速度|神券|京豆|好价|bug|\d+元|\d+券|\d+减\d+|\d+-\d+',
    'exclude': r'权限|水.?贴|什么|怎么|怎样|不能|不行|没有|反撸|求|啥|问|哪|吗|么|？|\?'
}
# 匹配群聊名称
MATCH_ROOMS = ['双11小分队']
# 全局存储数据
result = dict()
last_result = dict()
# 推送名单
user_names = list()


def main_handler():
    global result, last_result
    try:
        logging.info('临时文件：' + ZK_TMP_FILE)
        if not os.path.exists(ZK_TMP_FILE):
            logging.info('临时文件不存在')
        else:
            with open(ZK_TMP_FILE, 'r', encoding=UTF8_ENCODING) as f:
                result = json.load(f)
        logging.info('当前存储数据量：' + str(len(result.keys())))
        # zk首页热门内容
        d = py(ZK_BASE_URL, headers=REQUEST_HEADERS, encoding=GBK_ENCODING)
        d('#threadlisttableid tbody').each(deal_post)
        # 0818tuan
        d = py(TUAN_BASE_URL, headers=REQUEST_HEADERS, encoding=GB2312_ENCODING)
        d('.list-group > .list-group-item').each(deal_post_tuan)
    except Exception as ex:
        logging.exception('主任务运行异常：' + str(ex))
        raise ex
    finally:
        # 创建存储目录
        if not os.path.exists(BASE_DIR):
            os.makedirs(BASE_DIR)
        # 存储结果
        with open(ZK_TMP_FILE, 'w', encoding=UTF8_ENCODING) as f:
            # 超过数量清空
            if len(result.keys()) > 500:
                last_result.clear()
                last_result = result
                result = dict()
            logging.info('保存数据结果')
            json.dump(result, f)

# 每个帖子
def deal_post(i, e):
    global result
    match = re.match(r'normalthread_(\d+)', str(py(e).attr('id')))
    if match is None:
        return
    # 帖子主键
    post_id = match.group(1)
    # 已存在
    if is_result_include(post_id):
        return
    # 帖子标题
    title = py(e).find('th').text()
    if not is_keyword_valid(title):
        return
    # 帖子时间
    time = py(e).find('td:eq(1)').find('em').text()
    info = get_post_info(post_id, title=title, time=time)
    result[post_id] = info
    # 内容关键字判断
    if not is_keyword_valid(info['content'], 'content'):
        logging.info('内容关键字过滤：' + str(info))
        return
    logging.info('准备推送信息：' + str(info))
    send_msg(info)

def deal_post_tuan(i, e):
    global result
    info = dict()
    info['title'] = py(e).attr('title')
    url = py(e).attr('href')
    info['time'] = py(e).find('.badge-success').text()
    info['images'] = list()
    # 排除置顶
    if info['title'] is None or info['time'] == '':
        return
    # 排除非权限贴以及标题非关键字
    if len(re.findall(r'\[权\d*\]', info['title'])) == 0 \
        or not is_keyword_valid(info['title']) \
        or is_result_include(url):
        return
    info['url'] = os.path.dirname(TUAN_BASE_URL) + url
    logging.info('爬取链接：' + info['url'])
    d = py(info['url'], headers=REQUEST_HEADERS, encoding=GB2312_ENCODING)
    # 区块元素
    ele = d('.post-content>p:first').clone()
    for img in ele.find('img'):
        src = py(img).attr('src')
        if len(re.findall('.jpg|.jpeg|.png', src, re.I)) == 0:
            continue
        info['images'].append(src)
    info['content'] = py(re.sub(r'(<br/>\n?)+', '\n', ele.remove('img').html())).text()
    result[url] = info
    # 内容非关键字
    if not is_keyword_valid(info['content'], 'content'):
        logging.info('内容关键字过滤：' + str(info))
        return
    logging.info('准备推送信息：' + str(info))
    send_msg(info)

# 判读结果是否包含
def is_result_include(key):
    global result, last_result
    # 已存在
    if result.get(key) is not None or last_result.get(key) is not None:
        return True
    else:
        return False

# 判断是否符合关键字
def is_keyword_valid(text, check_type='title'):
    if check_type == 'title':
        if len(re.findall(KEYWORD['include'], text, re.I)) == 0 \
            or len(re.findall(KEYWORD['exclude'], text, re.I)) > 0:
            return False
        else:
            return True
    else:
        return False if len(re.findall(KEYWORD['exclude'], text, re.I)) > 0 else True

# 发送消息
def send_msg(info):
    # 推送用户名单
    global user_names
    files = list()
    content = '%s\n\n%s\n\n电脑版：%s' % (info['title'], info['content'], info['url'])
    for name in user_names:
        itchat.send_msg(content, toUserName=name)
        # 发送图片
        for url in info['images']:
            path = os.path.join(BASE_DIR, os.path.basename(url))
            files.append(path)
            f = open(path, 'wb')
            f.write(requests.get(url).content)
            f.close()
            itchat.send_image(path, toUserName=name)
        time.sleep(random.randint(2, 5))
    # 删除临时文件
    for path in files:
        if os.path.exists(path):
            os.remove(path)

# 获取帖子链接内容
def get_post_info(post_id, title=None, time=None):
    info = dict()
    info['url'] = ZK_POST_URL % post_id
    logging.info('爬取链接：' + info['url'])
    d = py(info['url'], headers=REQUEST_HEADERS, encoding=GBK_ENCODING)
    # 帖子标题
    post_title = d('#thread_subject').attr('title')
    # 帖子时间
    post_time = d('.pti:first>.authi:first').find('em:first').text().replace('发表于 ', '')
    # 帖子图片
    info['images'] = list()
    if post_title is None:
        info['title'] = None if title is None else title
        info['time'] = None if time is None else time
        info['content'] = d('#messagetext>p:first').text()
    else:
        info['title'] = post_title
        info['time'] = post_time
        ele = d('#postlist>div:first').find('tr:first').find('.t_f')
        info['content'] = '' if ele is None else py(ele.html()).remove('ignore_js_op').text()
        for e in d('.t_fsz:first').find('ignore_js_op').find('img'):
            e = py(e)
            if e.attr('aid') is None:
                continue
            src = e.attr('file')
            if len(re.findall('.jpg|.jpeg|.png', src, re.I)) == 0:
                continue
            info['images'].append(src)
    return info


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
            main_handler()
        except Exception as ex:
            logging.exception('主线程异常：' + str(ex))
        time.sleep(ZK_TASK_INTERVAL)
    # 退出登录
    itchat.logout()