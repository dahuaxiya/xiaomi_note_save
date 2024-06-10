import time

import requests
import json
from datetime import datetime
import re
from user_info import STR_COOKIE_MAIN, STR_COOKIE_EVERY_NOTE, URL_GET_NOTES, URL_GET_NOTE


# 排序指标，可以修改
def sortRule(obj):
    return obj['create_date']


# 将cookie字符串转为字典格式
def get_cookie(cookie_str):
    # 将cookie字符串转换为字典
    cookie_dict = {}
    for item in cookie_str.split('; '):
        key, value = item.split('=', 1)
        cookie_dict[key] = value
    return cookie_dict


def get_now():
    # 获取当前时间的时间戳（秒级别）
    timestamp_seconds = time.time()
    # 转换为毫秒级别
    timestamp_milliseconds = int(timestamp_seconds * 1000)
    return str(timestamp_milliseconds)

def get_folders():
    if len(folders_info) == 0:
        response = requests.get(URL_GET_NOTES, cookies=cookie_main)
        syncTag = response.json()['data']['syncTag']
        response = requests.get(URL_GET_NOTES+"&syncTag="+syncTag, cookies=cookie_main)
        for item in response.json()['data']['folders']:
            folders_obj[item['id']] = []
            folders_info[item['id']] = {"subject": item['subject'], "id": item['id'],
                                               "create_date": datetime.fromtimestamp(item['createDate'] / 1000),
                                               "modify_date": datetime.fromtimestamp(item['modifyDate'] / 1000)}


def nextPage(syncTag=None):
    url = URL_GET_NOTES
    ts = get_now()
    get_folders()   # 添加分类信息
    if syncTag:
        url += '&syncTag=' + syncTag

    url += '&ts=' + ts  # 添加时间戳参数
    try:
        response = requests.get(url, cookies=cookie_main)
    except:
        print("connection error")


    print("1: ")
    if response.status_code == 200:
        result = response.json()
        for entry in result['data']['entries']:
            print("2: ")
            detailUrl = URL_GET_NOTE + entry['id']
            try:
                detailResponse = requests.get(detailUrl, cookies=cookie_dict_every_note)
            except:
                print(f"error: {detailUrl} ")
                error_urls.append(detailUrl)
                continue

            if detailResponse.status_code == 200:
                detailInfo = detailResponse.json()['data']['entry']
                date = datetime.fromtimestamp(entry['createDate'] / 1000)
                modifyDate = datetime.fromtimestamp(entry['modifyDate'] / 1000)
                resultObj = {}
                resultObj['title'] = json.loads(detailInfo.get('extraInfo', '{}')).get('title', '无')
                resultObj['create_date'] = date
                resultObj['modify_date'] = modifyDate
                resultObj['content'] = detailInfo['content']
                resultObj['folderId'] = detailInfo['folderId']
                resultObj['colorId'] = detailInfo['colorId']
                print(detailUrl, '内容：', detailInfo['content'][:20])
                resultArray.append(resultObj)
                # 将笔记保存到分类字典中
                if (resultObj['folderId'] in folders_obj):
                    folders_obj[resultObj['folderId']].append(resultObj)
        if result['data']['entries']:
            nextPage(result['data']['syncTag'])


#             resultArray.sort(key=sortRule)
#             with open('output.txt', 'w', encoding='utf-8') as f:
#                 for resObj in resultArray:
#                     f.write('创建日期：' + dateFormat(resObj['create_date']) + '\n')
#                     f.write('修改日期：' + dateFormat(resObj['modify_date']) + '\n')
#                     f.write('标题：' + resObj['title'] + '\n')
#                     f.write('内容：' + remove_tags(resObj['content']) + '\n')
#                     f.write('-----------------------\n')
#                 print("内容已保存到 output.txt 文件中")

def dateFormat(date):
    return date.strftime('%Y-%m-%d %H:%M:%S')


def remove_tags(text):
    clean = re.compile('<.*?>')
    return re.sub(clean, '', text)


def write_note(resObj: dict, f):
    f.write('创建日期：' + dateFormat(resObj['create_date']) + '\n')
    f.write('修改日期：' + dateFormat(resObj['modify_date']) + '\n')
    f.write('标题：' + resObj['title'] + '\n')
    f.write('内容：' + remove_tags(resObj['content']) + '\n')
    f.write('-----------------------\n')


def write_folder_info(folderObj: dict, f):
    f.write('创建日期：' + dateFormat(folderObj['create_date']) + '\n')
    f.write('修改日期：' + dateFormat(folderObj['modify_date']) + '\n')
    f.write('主题：' + folderObj['subject'] + '\n')
    f.write('----------------------------------------------\n')


if __name__ == "__main__":
    resultArray = []
    error_urls = []
    folders_info = dict()
    folders_obj = dict()
    # 将获取目录的cookie字符串复制到此
    str_cookie_main = STR_COOKIE_MAIN
    # 将获取单条笔记的cookie字符串复制到此
    str_cookie_every_note = STR_COOKIE_EVERY_NOTE
    # 将cookie字符串转为字典
    cookie_main = get_cookie(str_cookie_main)
    cookie_dict_every_note = get_cookie(str_cookie_every_note)
    nextPage()
    # 将笔记写入output.md文件中
    with open('output.md', 'w', encoding='utf-8') as f:
        for resObj in resultArray:
            write_note(resObj=resObj, f=f)
        print("内容已保存到 output.md 文件中")

    for folderObj in folders_info.values():
        folder_subject = folderObj['subject']
        folder_id = folderObj['id']
        with open(f"folders_{folder_subject}.md", 'w', encoding='utf-8') as f:
            write_folder_info(folderObj=folderObj, f=f)
            for resObj in folders_obj[folder_id]:
                write_note(resObj=resObj, f=f)
        print(f"内容已保存到 folders_{folder_subject}.md 文件中")

    # 将未成功的笔记链接保存到error_urls.txt文件
    with open('error_urls.txt', 'w', encoding='utf-8') as f:
        for url in error_urls:
            f.write(url + '\n')
        print("error 内容已保存到文件error_urls.txt中")
