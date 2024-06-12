import os.path
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
        response = requests.get(URL_GET_NOTES + "&syncTag=" + syncTag, cookies=cookie_main)
        folders_info['2'] = {'subject': '私密空间', 'id': '2'}
        folders_obj['2'] = []
        for item in response.json()['data']['folders']:
            folders_obj[item['id']] = []
            folders_info[item['id']] = {"subject": item['subject'], "id": item['id'],
                                        "create_date": datetime.fromtimestamp(item['createDate'] / 1000),
                                        "modify_date": datetime.fromtimestamp(item['modifyDate'] / 1000)}


def download_note_imgs(img_ids: list):
    """
    下载列表中所有的图片文件到assets
    :param img_ids:
    :return:
    """
    for img_id in img_ids:
        if os.path.exists(f"assets/{img_id}.jpeg"):
            continue
        try:
            res = requests.get(
                url=f"https://i.mi.com/file/full?type=note_img&fileid={img_id}", allow_redirects=True,
                cookies=get_cookie(STR_COOKIE_EVERY_NOTE))
            if res.status_code == 200:
                with open(f"assets/{img_id}.jpeg", "wb") as file:
                    file.write(res.content)
                    print(f"图片：{img_id} 下载完成")
            else:
                print(f"图片{img_id}下载失败")
        except:
            print("图片下载失败")


def extract_imgids(text):
    """
    获取content中所有图片的id并返回
    :param text:
    :return: 图片id列表
    """
    pattern = re.compile(r'\b\d{10}\.[a-zA-Z0-9_-]{22}\b')
    matches = pattern.findall(text)
    return matches


def nextPage(syncTag=None):
    url = URL_GET_NOTES
    ts = get_now()
    get_folders()  # 添加分类信息
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
                img_ids = extract_imgids(detailInfo['content'])
                if len(img_ids) > 0:
                    download_note_imgs(img_ids=img_ids)
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
                if (str(resultObj['folderId']) in folders_obj): # 将key强转为str防止key为int类型
                    folders_obj[str(resultObj['folderId'])].append(resultObj)
        if result['data']['entries']:
            nextPage(result['data']['syncTag'])


def dateFormat(date):
    return date.strftime('%Y-%m-%d %H:%M:%S')


def remove_tags(text):
    clean = re.compile('<.*?>')
    return re.sub(clean, '', text)


def remove_tags_except_img(text):
    """
    将笔记内容中标签全部去除，若标签中有多媒体文件的fileid则保留fileid，并将所有fileid转为<img src="">形式
    :param text: 笔记的原始content
    :return: 经过处理后的content
    """

    # 正则表达式匹配含有特定格式字符串的标签
    fileid_pattern = re.compile(r'<[^>]*\b\d{10}\.[a-zA-Z0-9_-]{22}\b[^>]*>')

    # 查找所有含有特定格式字符串的标签
    fileid_tags = fileid_pattern.findall(text)

    # 提取特定格式的字符串
    fileids = [re.search(r'\b\d{10}\.[a-zA-Z0-9_-]{22}\b', tag).group(0) for tag in fileid_tags]
    place_holder = f"~!@@place_holder@@"
    # 替换含有特定格式字符串的标签为占位符
    text_with_placeholders = re.sub(fileid_pattern, place_holder, text)

    # 移除所有其他 HTML 标签
    text_cleaned = re.sub(r'</?[^>]+>', '', text_with_placeholders)

    # 恢复含有特定格式字符串的部分
    for fileid in fileids:
        text_cleaned = text_cleaned.replace(place_holder, fileid, 1)

    pattern = re.compile(r'\b\d{10}\.[a-zA-Z0-9_-]{22}\b')

    def replace_fileid(match):
        fileid = match.group(0)
        return f'<img src="assets/{fileid}.jpeg">'

    text_with_replaced_ids = re.sub(pattern, replace_fileid, text_cleaned)
    return text_with_replaced_ids


def write_note(resObj: dict, f):
    f.write('创建日期：' + dateFormat(resObj['create_date']) + '\n')
    f.write('修改日期：' + dateFormat(resObj['modify_date']) + '\n')
    f.write('标题：' + resObj['title'] + '\n')
    f.write('内容：' + remove_tags_except_img(resObj['content']) + '\n')
    f.write('\n')
    f.write('-----------------------\n')


def write_folder_info(folderObj: dict, f):
    if 'create_date' in folderObj:
        f.write('创建日期：' + dateFormat(folderObj['create_date']) + '\n')
    if 'modify_date' in folderObj:
        f.write('修改日期：' + dateFormat(folderObj['modify_date']) + '\n')
    f.write('主题：' + folderObj['subject'] + '\n')
    f.write('\n')
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
    # 创建存储多媒体资源的文件夹
    if not os.path.exists("assets"):
        os.mkdir("assets")

    nextPage()
    resultArray.sort(key=sortRule)  # 按照创建时间排序
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
