import csv
import time
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# 中国货币网债券信息接口
API_URL = "https://www.chinamoney.com.cn/ags/ms/cm-u-bond-md/BondMarketInfoListEN"
# 输出文件名
OUTPUT_FILE = "bond_data_2023_treasury.csv"

# CSV文件中需要保存的列名
COLUMNS = [
    "ISIN",
    "Bond Code",
    "Issuer",
    "Bond Type",
    "Issue Date",
    "Latest Rating",
]

# 创建并配置 Session
def create_session():
    session = requests.Session()

    # 配置重试策略
    # (1)当服务器临时返回 429、5xx 等状态码时，自动重试
    # (2)最多重试 3 次
    # (3)每次重试之间等待一定时间
    # (4)只对 POST 请求启用重试
    retry_strategy = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["POST"],
    )

    # 将重试策略挂载到 HTTP 和 HTTPS 请求上
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("https://", adapter)
    session.mount("http://", adapter)

    # 设置请求头，模拟浏览器访问
    session.headers.update({
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Referer": "https://www.chinamoney.com.cn/english/bdInfo/",
        "Origin": "https://www.chinamoney.com.cn",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    })

    return session

# 请求某一页债券数据。
# 参数：
# (1)session: 已配置好的 Session
# (2)page_no: 当前页码
# (3)page_size: 每页数据条数
# 返回：
# 当前页接口返回的 data 字段
def fetch_page(session, page_no, page_size=15):

    # bondType=100001 表示 Treasury Bond
    # issueYear=2023 表示发行年份为 2023 年
    payload = {
        "bondType": "100001",
        "issueYear": "2023",
        "pageNo": str(page_no),
        "pageSize": str(page_size),
    }

    try:
        # 发送 POST 请求
        response = session.post(API_URL, data=payload, timeout=20)
        # 如果 HTTP 状态码不是 2xx，则抛出异常
        response.raise_for_status()
        # 将 JSON 响应解析为 Python 字典
        data = response.json()
    except requests.exceptions.RequestException as e:
        # 捕获网络异常，例如连接失败、超时、HTTP 错误等
        raise RuntimeError(f"Request failed: {e}") from e
    except ValueError as e:
        # 捕获 JSON 解析失败
        raise RuntimeError("Response is not valid JSON.") from e

    # 校验接口返回结构是否符合预期
    if "data" not in data:
        raise RuntimeError(f"Unexpected response format: {data}")

    return data["data"]

# 从接口返回的一条债券记录中提取需要的字段。
# 参数：
# row: 接口返回的单条债券数据
# 返回：
# 字典，key 为 CSV 列名，value 为对应字段值
def parse_bond(row):
    return {
        # ISIN 编码
        "ISIN": row.get("isin", ""),
        # 债券代码
        "Bond Code": row.get("bondCode", ""),
        # 发行人
        "Issuer": row.get("entyFullName", ""),
        # 债券类型
        "Bond Type": row.get("bondType", ""),
        # 发行日期
        "Issue Date": row.get("issueStartDate", ""),
        # 最新评级
        "Latest Rating": row.get("debtRtng", ""),
    }

def main():
    # (1) 创建请求会话
    session = create_session()
    # (2) 先请求第一页，用于获取总页数
    first_page = fetch_page(session, page_no=1)
    # (3) pageTotal 表示总页数,如果接口没有返回 pageTotal，则默认只有 1 页
    total_pages = int(first_page.get("pageTotal", 1))

    all_rows = []

    # (4)按页请求所有数据
    for page_no in range(1, total_pages + 1):
        print(f"Fetching page {page_no}/{total_pages}...")

        # 获取当前页数据
        page_data = fetch_page(session, page_no=page_no)
        # resultList 是当前页表格数据列表
        result_list = page_data.get("resultList", [])

        # 逐条解析债券数据
        for row in result_list:
            all_rows.append(parse_bond(row))

        # 控制请求频率，避免短时间内请求过快
        time.sleep(0.3)

    # (5)将数据写入 CSV 文件
    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        # 写入表头
        writer.writeheader()
        # 写入所有数据行
        writer.writerows(all_rows)

    print(f"Saved {len(all_rows)} rows to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
