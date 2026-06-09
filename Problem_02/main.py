import re
from typing import List, Dict, Any


# 对原始文本做简单清洗：去掉多余换行，合并连续空白字符
def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


# 将中文日期格式转换为 YYYY-MM-DD
def normalize_chinese_date(date_str: str) -> str:
    pattern = r"(\d{4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日"
    match = re.search(pattern, date_str)

    if not match:
        return date_str

    year, month, day = match.groups()
    return f"{year}-{int(month):02d}-{int(day):02d}"


# 根据字段名返回内置正则表达式
def get_builtin_pattern(field_name: str) -> str:

    builtin_patterns = {
        # 提取股票代码：
        # 股票代码：600900.SH
        "标的证券": r"股票代码[：:]\s*([0-9]{6}\.[A-Z]{2})",

        # 提取换股期限对应的两个中文日期：
        # 即 2023 年 6 月 2 日至 2027 年 6 月 1 日止
        "换股期限": (
            r"换股期限.*?"
            r"(\d{4}\s*年\s*\d{1,2}\s*月\s*\d{1,2}\s*日)"
            r"\s*至\s*"
            r"(\d{4}\s*年\s*\d{1,2}\s*月\s*\d{1,2}\s*日)"
        ),
    }

    if field_name not in builtin_patterns:
        raise ValueError(f"No built-in regex pattern for field: {field_name}")

    return builtin_patterns[field_name]


# 根据单个字段规则提取匹配结果
# 返回逻辑：
#  1. 没有匹配到，返回 None
#  2. 只有一个捕获组，返回字符串
#  3. 有多个捕获组，返回列表
#  4. 对换股期限字段，额外做日期格式标准化
def extract_value(text: str, field_name: str, regex_pattern: str) -> Any:

    if regex_pattern == "*自定义*":
        regex_pattern = get_builtin_pattern(field_name)

    match = re.search(regex_pattern, text, flags=re.S)

    if not match:
        return None

    groups = match.groups()

    if len(groups) == 0:
        value = match.group(0)
    elif len(groups) == 1:
        value = groups[0]
    else:
        value = list(groups)

    # 对日期字段进行格式转换
    if field_name == "换股期限":
        if isinstance(value, list):
            value = [normalize_chinese_date(item) for item in value]
        else:
            value = normalize_chinese_date(value)

    return value


# 自定义正则匹配函数
def reg_search(text: str, regex_list: List[Dict[str, str]]) -> List[Dict[str, Any]]:

    cleaned_text = normalize_text(text)
    result = []

    for regex_group in regex_list:
        item = {}

        for field_name, regex_pattern in regex_group.items():
            item[field_name] = extract_value(
                cleaned_text,
                field_name,
                regex_pattern
            )

        result.append(item)

    return result


if __name__ == "__main__":
    text = """
    标的证券：本期发行的证券为可交换为发行人所持中国长江电力股份
    有限公司股票（股票代码：600900.SH，股票简称：长江电力）的可交换公司债
    券。
    换股期限：本期可交换公司债券换股期限自可交换公司债券发行结束
    之日满 12 个月后的第一个交易日起至可交换债券到期日止，即 2023 年 6 月 2
    日至 2027 年 6 月 1 日止。
    """

    regex_list = [
        {
            "标的证券": "*自定义*",
            "换股期限": "*自定义*",
        }
    ]

    print(reg_search(text, regex_list))
