# coding=utf-8

import csv
import glob
from utils import extract_seg
from utils import sentence_result
from utils import remove_duplicate_elements
from utils import find_element


def get_event_elements(case_file):
    """
    将案件中属于同一事件要素的词语合并，最终返回完整的事件要素
    :param case_file: 记录单个案件的文本文件
    :return event_elements: 返回一个字典，键为事件要素类型，值为对应的事件要素组成的list
    """
    words = []  # 保存所有属于事件要素的单词
    element_types = []  # 保存上述单词对应的事件要素类型

    with open(case_file, "r", encoding='utf-8') as f1:
        rows = []
        # 将文本转换成list，方便后续处理
        for line in f1.readlines():
            rows.append(line.strip("\n").split("\t"))

        for index, row in enumerate(rows):
            if "S" in row[-1]:
                # S出现在最后一个位置，说明这是一个单独的事件要素，将其加入words列表
                words.append(row[0])
                element_types.append(row[-1][-1])

            elif "B" in row[-1]:
                # 处理由多个单词组成的事件要素
                words.append(row[0])
                element_types.append(row[-1][-1])
                j = index + 1
                while "I" in rows[j][-1] or "E" in rows[j][-1]:
                    words[-1] += rows[j][0]
                    j += 1
                    if j == len(rows):
                        break

        # 将事件要素进行分类（将words列表中的元素按照类别分成6类）
        T = []  # 事故类型
        K = []  # 罪名
        D = []  # 主次责任
        P = []  # 积极因素（减刑因素）
        N = []  # 消极因素（加刑因素）
        R = []  # 判决结果

        for i in range(len(element_types)):
            if element_types[i] == "T":
                T.append(words[i])
            elif element_types[i] == "K":
                K.append(words[i])
            elif element_types[i] == "D":
                D.append(words[i])
            elif element_types[i] == "P":
                P.append(words[i])
            elif element_types[i] == "N":
                N.append(words[i])
            elif element_types[i] == "R":
                R.append(words[i])

        # 为了防止CRF未能抽取出全部的事件要素，因此使用规则化的方法，从原始文本中直接提取出部分事件要素，作为补充
        case = ""  # case是完整的案件内容
        for idx in range(len(rows)):
            case += rows[idx][0]

        if "无证" in case or "驾驶资格" in case:
            N.append("无证驾驶")
        if "无号牌" in case or "牌照" in case or "无牌" in case:
            N.append("无牌驾驶")
        if "酒" in case:
            N.append("酒后驾驶")
        if "吸毒" in case or "毒品" in case or "毒驾" in case:
            N.append("吸毒后驾驶")
        if "超载" in case:
            N.append("超载")
        if "逃逸" in case or "逃离" in case:
            N.append("逃逸")
        if ("有前科" in case or "有犯罪前科" in case) and (
                "无前科" not in case and "无犯罪前科" not in case):
            N.append("有犯罪前科")

        # 整理抽取结果
        event_elements = dict()  # 用字典存储各类事件要素
        event_elements["事故类型"] = remove_duplicate_elements(T)
        event_elements["罪名"] = remove_duplicate_elements(K)
        event_elements["主次责任"] = remove_duplicate_elements(D)
        event_elements["减刑因素"] = remove_duplicate_elements(P)
        event_elements["加刑因素"] = remove_duplicate_elements(N)
        event_elements["判决结果"] = remove_duplicate_elements(R)

        # 打印出完整的事件要素
        # for key, value in event_elements.items():
        #     print(key, value)

        return event_elements


def get_patterns_from_dict(event_elements):
    """
    将提取出的事件要素转换成特征
    :param event_elements: 字典形式的事件要素
    :return patterns: 字典形式的特征
    """
    patterns = dict()

    # 从事件要素中的"加刑因素"提取出三个特征：01死亡人数、02重伤人数、03轻伤人数
    patterns["01死亡人数"], patterns["02重伤人数"], patterns["03轻伤人数"] = extract_seg(
        "".join(event_elements["加刑因素"]))

    # 从事件要素中的"主次责任"提取出特征：04责任认定
    patterns["04责任认定"] = find_element(event_elements["主次责任"], "全部责任")

    # 从事件要素中的"加刑因素"提取出8个特征
    patterns["05是否酒后驾驶"] = find_element(event_elements["加刑因素"], "酒")
    patterns["06是否吸毒后驾驶"] = find_element(event_elements["加刑因素"], "毒")
    patterns["07是否无证驾驶"] = find_element(event_elements["加刑因素"], "驾驶证", "证")
    patterns["08是否无牌驾驶"] = find_element(event_elements["加刑因素"], "牌照", "牌")
    patterns["09是否不安全驾驶"] = find_element(event_elements["加刑因素"], "安全")
    patterns["10是否超载"] = find_element(event_elements["加刑因素"], "超载")
    patterns["11是否逃逸"] = find_element(event_elements["加刑因素"], "逃逸", "逃离")
    patterns["是否初犯偶犯"] = 1 - int(find_element(event_elements["加刑因素"], "前科"))

    # 从事件要素中的"减刑因素"提取出7个特征
    patterns["12是否抢救伤者"] = find_element(event_elements["减刑因素"], "抢救", "施救")
    patterns["13是否报警"] = find_element(event_elements["减刑因素"], "报警", "自首", "投案")
    patterns["14是否现场等待"] = find_element(event_elements["减刑因素"], "现场", "等候")
    patterns["15是否赔偿"] = find_element(event_elements["减刑因素"], "赔偿")
    patterns["16是否认罪"] = find_element(event_elements["减刑因素"], "认罪")
    patterns["17是否如实供述"] = find_element(event_elements["减刑因素"], "如实")
    if patterns["是否初犯偶犯"] == 0:
        patterns["18是否初犯偶犯"] = "0"
    else:
        patterns["18是否初犯偶犯"] = "1"
    return patterns


def label_case(file, is_label=False):
    """
    给数据打标签
    :param is_label: 是否需要将刑期分类，默认不分类
    :param file: 无标签的preprocessed_data.txt
    :return:
    """
    f = open(file, 'r', encoding='utf-8')
    cases = f.readlines()
    labels = []
    for case in cases:
        labels.append(sentence_result(case))
    f.close()

    # 分类
    if is_label:
        for i in range(len(labels)):
            if 0 <= labels[i] <= 5:
                labels[i] = 0
            elif 6 <= labels[i] <= 18:
                labels[i] = 1
            elif 19 <= labels[i] <= 24:
                labels[i] = 2
            elif 25 <= labels[i] <= 36:
                labels[i] = 3
            else:
                labels[i] = 4

    return labels


headers = [
    '01死亡人数',
    "02重伤人数",
    "04责任认定",
    "05是否酒后驾驶",
    "06是否吸毒后驾驶",
    "07是否无证驾驶",
    "08是否无牌驾驶",
    "09是否不安全驾驶",
    "10是否超载",
    "11是否逃逸",
    "12是否抢救伤者",
    "13是否报警",
    "14是否现场等待",
    "15是否赔偿",
    "16是否认罪",
    "18是否初犯偶犯",
    "判决结果"]
rows = []

# 提取标签
labels = label_case(
    "/home/zhangshiwei/Event-Extraction/01数据预处理/preprocessed_data.txt",
    is_label=True)
num_cases = len(glob.glob(
    "/home/zhangshiwei/Event-Extraction/06判决结果预测/特征提取/data/单个案件/*.txt"))

f1 = open(
    "/home/zhangshiwei/Event-Extraction/01数据预处理/preprocessed_data.txt",
    "r",
    encoding="utf-8")
cases = f1.readlines()

for i in range(1, num_cases + 1):
    file_name = "data/单个案件/" + str(i) + ".txt"
    event_elements = get_event_elements(file_name)
    patterns = get_patterns_from_dict(event_elements)

    # 因为目前CRF提取的效果还不够好，伤亡情况可能没有提取出来
    # 保险起见，对整个案件进行提取死亡人数等3个特征，而非事件抽取的结果
    patterns['01死亡人数'], patterns['02重伤人数'], patterns['03轻伤人数'] = extract_seg(cases[i - 1])
    patterns["判决结果"] = labels[i - 1]
    del patterns["是否初犯偶犯"]
    del patterns["03轻伤人数"]
    del patterns["17是否如实供述"]
    rows.append(patterns)
f1.close()

# 写回数据
with open("data.csv", "w", newline='') as f:
    f_csv = csv.DictWriter(f, headers)
    # f_csv.writeheader()
    f_csv.writerows(rows)
