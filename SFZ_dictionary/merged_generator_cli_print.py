#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
   six_code       不携带 -dict 时使用，指定 6 位第一部分，执行生成单条功能
   -dict DICT     执行批量随机功能，并指定 6 位字典文件路径
   -sd            指定开始日期，格式 YYYYMMDD；不指定时默认系统日期往前 30000 天
   -ed            指定结束日期，格式 YYYYMMDD；不指定时默认系统当前日期
   -norm          激活正态分布日期随机；不指定时使用均匀随机日期
   -s             指定按性别限制奇偶性：M=奇数，F=偶数；不指定则不限制
   -sn            指定 3 位顺序码起始值，范围 1-999；需要与 -snd 同时使用
   -snd           指定 3 位顺序码结束值，范围 1-999；需要与 -sn 同时使用
   -o             指定输出路径和文件名
   -n             指定输出条目数量；不指定默认 1
"""

from __future__ import annotations

import argparse
import csv
import random
import sys
from pathlib import Path
from datetime import datetime, timedelta


WEIGHTS = [7, 9, 10, 5, 8, 4, 2, 1, 6, 3, 7, 9, 10, 5, 8, 4, 2]

CHECK_CODE_MAP = {
    0: "1",
    1: "0",
    2: "X",
    3: "9",
    4: "8",
    5: "7",
    6: "6",
    7: "5",
    8: "4",
    9: "3",
    10: "2",
}



# 通用工具函数


def calculate_check_code(first_17_digits: str) -> str:
    """根据前 17 位计算校验码。"""
    if len(first_17_digits) != 17:
        raise ValueError("用于计算校验码的字符串必须正好是 17 位。")

    if not first_17_digits.isdigit():
        raise ValueError("前 17 位必须全部是数字。")

    total = sum(int(digit) * weight for digit, weight in zip(first_17_digits, WEIGHTS))
    remainder = total % 11
    return CHECK_CODE_MAP[remainder]


def get_default_output_path() -> Path:
    """默认输出到当前用户桌面的 out.txt。"""
    return Path.home() / "Desktop" / "out.txt"


def get_default_date_range() -> tuple[str, str]:
    """
    获取默认日期范围。

    正常情况下：
      -ed 使用系统当前日期；
      -sd 使用当前日期往前 30000 天。

    如果系统日期年份小于 2025，认为系统时间可能异常；
    在用户没有显式输入 -sd / -ed 时，继续使用默认值。
    """
    today = datetime.now()

    if today.year < 2025:
        return "19610101", "20261231"

    start_date = today - timedelta(days=30000)
    return start_date.strftime("%Y%m%d"), today.strftime("%Y%m%d")


def parse_yyyymmdd(date_str: str) -> datetime:
    """解析 8 位纯数字日期，格式 YYYYMMDD。"""
    if len(date_str) != 8 or not date_str.isdigit():
        raise ValueError(f"日期必须是 8 位纯数字格式 YYYYMMDD：{date_str}")

    try:
        return datetime.strptime(date_str, "%Y%m%d")
    except ValueError:
        raise ValueError(f"日期不是合法日期：{date_str}")


def normalize_dictionary_token(raw_value: str) -> str:
    """清理字典单元格中的常见包裹字符和不可见头部。"""
    value = raw_value.strip().lstrip("\ufeff")

    # 兼容 CSV 中常见的引号包裹。
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        value = value[1:-1].strip()

    return value


def extract_dictionary_values_from_line(line: str, suffix: str) -> list[str]:
    """从一行文本中提取候选 6 位字典值。"""
    stripped = line.strip().lstrip("\ufeff")

    if not stripped:
        return []

    # 允许常见注释行，方便维护字典文件。
    if stripped.startswith("#") or stripped.startswith("//"):
        return []

    if suffix == ".csv":
        try:
            row = next(csv.reader([line]))
        except csv.Error as e:
            raise ValueError(f"CSV 行解析失败：{line.strip()}；原因：{e}")
        return [normalize_dictionary_token(cell) for cell in row]

    if suffix in {".tsv", ".tab"}:
        return [normalize_dictionary_token(cell) for cell in line.split("\t")]

    # .txt / .list / .dict / 无扩展名：兼容一行一个值，也兼容逗号、空白、分号分隔。
    normalized = stripped.replace(",", " ").replace(";", " ").replace("\t", " ")
    return [normalize_dictionary_token(part) for part in normalized.split()]


def is_probable_header(value: str) -> bool:
    """判断常见表头字段，避免 CSV/TXT 第一行写 code/six_code/area_code 时报错。"""
    normalized = value.strip().lower().replace("-", "_").replace(" ", "_")
    return normalized in {
        "code",
        "six_code",
        "area_code",
        "district_code",
        "region_code",
        "行政区划码",
        "地区码",
        "区划码",
    }


def load_dictionary(file_path: str, expected_length: int = 6) -> list[str]:
    """
    读取第一部分的指定长度字典文件。

    支持：
      - .txt / .list / .dict / 无扩展名：一行一个值，或逗号/空白/分号分隔；
      - .csv：按 CSV 规则读取，可含表头；
      - .tsv / .tab：按制表符分隔读取；
      - UTF-8 BOM / UTF-8-SIG 常见头部；
      - # 或 // 开头的注释行。

    只收集指定长度的纯数字字段；其他非空字段若不是表头，会报错以避免误读脏数据。
    """
    path = Path(file_path).expanduser()

    if not path.exists():
        raise FileNotFoundError(f"字典文件不存在：{file_path}")

    suffix = path.suffix.lower()
    values: list[str] = []

    with path.open("r", encoding="utf-8-sig", newline="") as f:
        for line_number, line in enumerate(f, start=1):
            candidates = extract_dictionary_values_from_line(line, suffix)

            for candidate in candidates:
                value = normalize_dictionary_token(candidate)

                if not value:
                    continue

                if is_probable_header(value):
                    continue

                if len(value) != expected_length:
                    raise ValueError(
                        f"字典文件 {file_path} 第 {line_number} 行存在长度不是 {expected_length} 位的字段：{value}"
                    )

                if not value.isdigit():
                    raise ValueError(
                        f"字典文件 {file_path} 第 {line_number} 行存在非数字字段：{value}。"
                        "因为校验码需要逐位数字计算，所以前 17 位必须全是数字。"
                    )

                values.append(value)

    if not values:
        raise ValueError(f"字典文件为空或没有有效内容：{file_path}")

    return values



# 日期与第三部分生成逻辑


def random_date_normal(start_date_str: str, end_date_str: str) -> str:
    """在两个日期之间按正态分布随机取日期，越靠近中间值概率越高。"""
    start_date = parse_yyyymmdd(start_date_str)
    end_date = parse_yyyymmdd(end_date_str)

    if start_date > end_date:
        raise ValueError("开始日期不能晚于结束日期。")

    days_range = (end_date - start_date).days

    if days_range == 0:
        return start_date.strftime("%Y%m%d")

    mean = days_range / 2
    std_dev = days_range / 6

    while True:
        offset = int(round(random.gauss(mean, std_dev)))
        if 0 <= offset <= days_range:
            return (start_date + timedelta(days=offset)).strftime("%Y%m%d")


def random_date_uniform(start_date_str: str, end_date_str: str) -> str:
    """在两个日期之间均匀随机取日期，每一天概率相同。"""
    start_date = parse_yyyymmdd(start_date_str)
    end_date = parse_yyyymmdd(end_date_str)

    if start_date > end_date:
        raise ValueError("开始日期不能晚于结束日期。")

    days_range = (end_date - start_date).days
    offset = random.randint(0, days_range)
    return (start_date + timedelta(days=offset)).strftime("%Y%m%d")


def generate_third_part(
    gender: str | None = None,
    sequence_start: int | None = None,
    sequence_end: int | None = None,
) -> str:
    """
    第三部分生成逻辑。

    默认逻辑：001-050 占 65%，051-100 占 35%。
    指定 sequence_start 和 sequence_end 时：在指定闭区间内随机取值。

    gender 为 M 时限制为奇数；gender 为 F 时限制为偶数；不传则不限制奇偶。
    """
    if (sequence_start is None) != (sequence_end is None):
        raise ValueError("-sn 和 -snd 必须同时指定，不能只指定其中一个。")

    if sequence_start is None and sequence_end is None:
        if random.random() < 0.65:
            num_pool = list(range(1, 51))
        else:
            num_pool = list(range(51, 101))
    else:
        if not (1 <= sequence_start <= 999):
            raise ValueError("-sn 必须在 1 到 999 之间。")
        if not (1 <= sequence_end <= 999):
            raise ValueError("-snd 必须在 1 到 999 之间。")
        if sequence_start > sequence_end:
            raise ValueError("-sn 不能大于 -snd。")

        num_pool = list(range(sequence_start, sequence_end + 1))

    if gender == "M":
        num_pool = [n for n in num_pool if n % 2 != 0]
    elif gender == "F":
        num_pool = [n for n in num_pool if n % 2 == 0]

    if not num_pool:
        raise ValueError("指定的顺序码范围在应用性别奇偶限制后没有可用值。")

    return f"{random.choice(num_pool):03d}"


def generate_one_from_dict(
    dict_6: list[str],
    start_date: str,
    end_date: str,
    gender: str | None = None,
    use_normal_distribution: bool = False,
    sequence_start: int | None = None,
    sequence_end: int | None = None,
) -> str:
    """从字典随机选择 6 位第一部分，生成一条完整结果。"""
    part1 = random.choice(dict_6)
    return generate_one_from_part1(
        part1,
        start_date,
        end_date,
        gender,
        use_normal_distribution,
        sequence_start,
        sequence_end,
    )


def generate_one_from_part1(
    part1: str,
    start_date: str,
    end_date: str,
    gender: str | None = None,
    use_normal_distribution: bool = False,
    sequence_start: int | None = None,
    sequence_end: int | None = None,
) -> str:
    """使用指定 6 位第一部分生成一条完整结果。"""
    if len(part1) != 6 or not part1.isdigit():
        raise ValueError("生成单条模式需要提供 6 位数字，例如：110101")

    if use_normal_distribution:
        part2 = random_date_normal(start_date, end_date)
    else:
        part2 = random_date_uniform(start_date, end_date)

    part3 = generate_third_part(
        gender=gender,
        sequence_start=sequence_start,
        sequence_end=sequence_end,
    )

    first_17_digits = part1 + part2 + part3
    return first_17_digits + calculate_check_code(first_17_digits)



# CLI 入口


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="非交互式生成器：携带 -dict 执行批量随机；不携带 -dict 默认执行生成单条。"
    )

    parser.add_argument(
        "six_code",
        nargs="?",
        help="生成单条模式使用：6 位第一部分，例如 110101。",
    )
    parser.add_argument(
        "-dict",
        dest="dict_path",
        metavar="DICT",
        help="执行批量随机功能，并指定 6 位字典文件路径；支持 .txt/.csv/.tsv 等常见文本格式。",
    )
    parser.add_argument("-sd", default=None, help="指定开始日期，格式 YYYYMMDD。默认：系统日期往前 30000 天；若系统年份小于 2025 则默认 19610101。")
    parser.add_argument("-ed", default=None, help="指定结束日期，格式 YYYYMMDD。默认：系统当前日期；若系统年份小于 2025 则默认 20261231。")
    parser.add_argument(
        "-norm",
        action="store_true",
        help="激活正态分布日期随机；不指定时使用均匀随机日期。",
    )
    parser.add_argument(
        "-s",
        choices=["M", "F", "m", "f"],
        help="指定按性别限制奇偶性：M=奇数，F=偶数。不指定则不限制。",
    )
    parser.add_argument(
        "-sn",
        type=int,
        default=None,
        help="指定 3 位顺序码起始值，范围 1-999；需要与 -snd 同时使用。不指定时使用默认加权逻辑。",
    )
    parser.add_argument(
        "-snd",
        type=int,
        default=None,
        help="指定 3 位顺序码结束值，范围 1-999；需要与 -sn 同时使用。不指定时使用默认加权逻辑。",
    )
    parser.add_argument("-o", default=None, help="指定输出路径和文件名。")
    parser.add_argument("-n", type=int, default=1, help="指定输出条目数量。默认：1。")

    return parser


def write_results(output_path: str | Path, results: list[str]) -> Path:
    path = Path(output_path).expanduser()
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as f:
        for item in results:
            f.write(item + "\n")

    return path


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        gender = args.s.upper() if args.s else None

        if args.dict_path and args.six_code:
            raise ValueError("不能同时指定 six_code 和 -dict；二者分别对应生成单条模式和批量随机模式。")

        default_sd, default_ed = get_default_date_range()
        start_date_str = args.sd or default_sd
        end_date_str = args.ed or default_ed

        # 提前校验日期，避免生成到一半才报错。
        start_date = parse_yyyymmdd(start_date_str)
        end_date = parse_yyyymmdd(end_date_str)
        if start_date > end_date:
            raise ValueError("开始日期不能晚于结束日期。")

        count = args.n
        if count <= 0:
            raise ValueError("输出条目数量 -n 必须大于 0。")

        if (args.sn is None) != (args.snd is None):
            raise ValueError("-sn 和 -snd 必须同时指定，不能只指定其中一个。")
        if args.sn is not None and args.snd is not None:
            if not (1 <= args.sn <= 999):
                raise ValueError("-sn 必须在 1 到 999 之间。")
            if not (1 <= args.snd <= 999):
                raise ValueError("-snd 必须在 1 到 999 之间。")
            if args.sn > args.snd:
                raise ValueError("-sn 不能大于 -snd。")
            if gender == "M" and not any(n % 2 != 0 for n in range(args.sn, args.snd + 1)):
                raise ValueError("指定的顺序码范围没有可用于 M 的奇数值。")
            if gender == "F" and not any(n % 2 == 0 for n in range(args.sn, args.snd + 1)):
                raise ValueError("指定的顺序码范围没有可用于 F 的偶数值。")

        if args.dict_path:
            mode = "批量随机"
            dict_6 = load_dictionary(args.dict_path, 6)
            results = [
                generate_one_from_dict(
                    dict_6=dict_6,
                    start_date=start_date_str,
                    end_date=end_date_str,
                    gender=gender,
                    use_normal_distribution=args.norm,
                    sequence_start=args.sn,
                    sequence_end=args.snd,
                )
                for _ in range(count)
            ]
        else:
            mode = "生成单条"
            if not args.six_code:
                raise ValueError(
                    "生成单条模式需要提供 6 位数字，例如："
                    "python3 merged_generator_cli_print.py 110101 -sd 19990522 -ed 19990522"
                )
            results = [
                generate_one_from_part1(
                    part1=args.six_code,
                    start_date=start_date_str,
                    end_date=end_date_str,
                    gender=gender,
                    use_normal_distribution=args.norm,
                    sequence_start=args.sn,
                    sequence_end=args.snd,
                )
                for _ in range(count)
            ]

        # 生成单条模式：不指定 -o 且真的只生成 1 条时，直接打印结果到屏幕。
        if mode == "生成单条" and args.o is None and count == 1:
            print(results[0])
            return 0

        output_file = write_results(args.o or get_default_output_path(), results)
        print(f"生成完成：{output_file}")
        print(f"模式：{mode}")
        print(f"条目数量：{count}")
        return 0

    except (ValueError, FileNotFoundError) as e:
        print(f"错误：{e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"运行过程中出现未知错误：{e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
