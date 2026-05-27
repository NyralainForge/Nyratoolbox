#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import csv
import random
import re
from pathlib import Path


DEFAULT_SUFFIXES = ["@139.com", "@163.com", "@162.com"]


def load_dict_file(file_path: str) -> list[str]:
    """
    读取 7 位数字字典文件。

    """
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"字典文件不存在: {file_path}")

    suffix = path.suffix.lower()
    values: list[str] = []

    def is_comment_or_empty(line: str) -> bool:
        stripped = line.strip()
        return (
            not stripped
            or stripped.startswith("#")
            or stripped.startswith("//")
        )

    def add_token(token: str) -> None:
        token = token.strip()

        if not token:
            return

        # CSV / TSV 表头或说明字段自动跳过
        if not token.isdigit():
            return

        if len(token) != 7:
            raise ValueError(f"字典中存在非法内容，不是 7 位数字: {token}")

        values.append(token)

    with path.open("r", encoding="utf-8-sig", newline="") as f:
        if suffix == ".csv":
            reader = csv.reader(
                line for line in f
                if not is_comment_or_empty(line)
            )

            for row in reader:
                for cell in row:
                    add_token(cell)

        elif suffix in {".tsv", ".tab"}:
            reader = csv.reader(
                (line for line in f if not is_comment_or_empty(line)),
                delimiter="\t"
            )

            for row in reader:
                for cell in row:
                    add_token(cell)

        elif suffix in {".txt", ".list", ".dict"}:
            for line in f:
                if is_comment_or_empty(line):
                    continue

                tokens = re.split(r"[\s,;]+", line.strip())

                for token in tokens:
                    add_token(token)

        else:
            raise ValueError(
                f"不支持的字典格式: {suffix}，"
                "仅支持 .txt / .list / .dict / .csv / .tsv / .tab"
            )

    if not values:
        raise ValueError("字典文件为空，或没有有效的 7 位数字")

    # 字典内部去重，保持原始顺序
    return list(dict.fromkeys(values))


def validate_prefix(prefix: str) -> str:
    """
    校验手动输入的第一部分。
    """
    if not prefix.isdigit() or len(prefix) != 7:
        raise ValueError("第一部分必须是 7 位数字")

    return prefix


def normalize_suffix(mail_suffix: str | None) -> str | None:
    """
    规范化 -m 参数。

    示例：
    - @163.com -> @163.com
    - 163.com  -> @163.com
    """
    if mail_suffix is None:
        return None

    mail_suffix = mail_suffix.strip()

    if not mail_suffix:
        raise ValueError("-m 后缀不能为空")

    if not mail_suffix.startswith("@"):
        mail_suffix = "@" + mail_suffix

    if not re.fullmatch(r"@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", mail_suffix):
        raise ValueError(f"邮箱后缀格式不合法: {mail_suffix}")

    return mail_suffix.lower()


def generate_normal_email(prefixes: list[str], mail_suffix: str | None = None) -> str:
    """
    生成普通模式结果：
    7 位前缀 + 4 位随机数字 + 邮箱后缀
    """
    prefix = random.choice(prefixes)
    suffix_number = f"{random.randint(0, 9999):04d}"

    if mail_suffix:
        suffix_mail = mail_suffix
    else:
        suffix_mail = random.choice(DEFAULT_SUFFIXES)

    return prefix + suffix_number + suffix_mail


def random_digits(length: int) -> str:
    """
    生成指定长度的随机数字。

    第一位不为 0，避免出现“看起来不是 N 位”的结果。
    """
    if length <= 0:
        raise ValueError("数字长度必须大于 0")

    first = random.choice("123456789")
    rest = "".join(random.choice("0123456789") for _ in range(length - 1))

    return first + rest


def random_qq_length_normal() -> int:
    """
    -q 单独使用时：
    随机 9 - 11 位数字。
    """
    return random.randint(9, 11)


def random_qq_length_weighted() -> int:
    """
    -qn 使用时：
    随机 7 - 11 位数字。

    权重：
    - 10 位：50%
    - 9 位：35%
    - 11 位：10%
    - 7 - 8 位：5%
    """
    bucket = random.choices(
        population=["10", "9", "11", "7-8"],
        weights=[50, 35, 10, 5],
        k=1
    )[0]

    if bucket == "10":
        return 10

    if bucket == "9":
        return 9

    if bucket == "11":
        return 11

    return random.choice([7, 8])


def generate_qq_email(
    q_length: int | None = None,
    weighted: bool = False
) -> str:
    """
    生成 QQ 数字邮箱。

    - -q：
      q_length 为 None 时，随机 9 - 11 位
      q_length 有值时，使用指定长度

    - -qn：
      weighted=True 时，使用加权长度
    """
    if weighted:
        length = random_qq_length_weighted()
    else:
        length = q_length if q_length is not None else random_qq_length_normal()

    number = random_digits(length)

    return number + "@qq.com"


def get_default_output_path() -> Path:
    """
    默认输出到桌面 out.txt。
    """
    desktop = Path.home() / "Desktop"
    return desktop / "out.txt"


def parse_q_length(q_value: str | None) -> int | None:
    """
    解析 -q 的可选长度参数。

    - 没有 -q：None
    - 单独 -q：None
    - -q 10：10
    """
    if q_value is None:
        return None

    if q_value == "__AUTO__":
        return None

    if not q_value.isdigit():
        raise ValueError("-q 后面的长度参数必须是正整数，例如：-q 10")

    length = int(q_value)

    if length <= 0:
        raise ValueError("-q 后面的长度必须大于 0")

    return length


def main():
    parser = argparse.ArgumentParser(
        description="生成随机数字邮箱：普通模式或 QQ 数字邮箱模式"
    )

    parser.add_argument(
        "prefix",
        nargs="?",
        help="不使用 -dict / -q / -qn 时，直接输入 7 位数字作为第一部分"
    )

    parser.add_argument(
        "-dict",
        dest="dict_file",
        help="挂载字典文件，每个值应为 7 位数字"
    )

    parser.add_argument(
        "-n",
        dest="count",
        type=int,
        default=1,
        help="输出条目个数，默认为 1"
    )

    parser.add_argument(
        "-o",
        dest="output",
        help="输出文件路径，默认为桌面 out.txt"
    )

    parser.add_argument(
        "-m",
        dest="mail_suffix",
        help="指定普通模式邮箱后缀，例如 @163.com 或 163.com；不指定则随机使用 @139.com / @163.com / @162.com"
    )

    parser.add_argument(
        "-q",
        dest="q_value",
        nargs="?",
        const="__AUTO__",
        help="QQ 数字邮箱模式。单独使用随机 9-11 位；也可指定长度，例如：-q 10"
    )

    parser.add_argument(
        "-qn",
        dest="q_weighted",
        action="store_true",
        help="QQ 数字邮箱加权模式：10位50%，9位35%，11位10%，7-8位5%"
    )

    args = parser.parse_args()

    if args.count <= 0:
        raise ValueError("-n 必须是大于 0 的整数")

    if args.q_value is not None and args.q_weighted:
        raise ValueError("-q 和 -qn 不能同时使用")

    mail_suffix = normalize_suffix(args.mail_suffix)

    q_mode = args.q_value is not None
    qn_mode = args.q_weighted
    qq_mode = q_mode or qn_mode

    q_length = parse_q_length(args.q_value) if q_mode else None

    prefixes: list[str] = []

    if args.dict_file:
        if args.prefix:
            raise ValueError("使用 -dict 时，不需要再手动输入 7 位数字参数")
        prefixes = load_dict_file(args.dict_file)
    else:
        # 非 QQ 模式下，必须手动输入 7 位前缀
        # QQ 模式下，可以不输入前缀
        if not qq_mode:
            if not args.prefix:
                raise ValueError("未使用 -dict / -q / -qn 时，必须直接输入一个 7 位数字")
            prefixes = [validate_prefix(args.prefix)]
        else:
            if args.prefix:
                raise ValueError("使用 -q 或 -qn 且不使用 -dict 时，不需要输入 7 位前缀")

    results = set()

    suffix_count = 1 if mail_suffix else len(DEFAULT_SUFFIXES)

    normal_max_possible = len(prefixes) * 10000 * suffix_count if prefixes else 0

    # QQ 模式理论空间非常大，这里只对普通模式做严格上限校验
    if not qq_mode and args.count > normal_max_possible:
        raise ValueError(
            f"要求生成 {args.count} 条，但普通模式最多只能生成 {normal_max_possible} 条不重复结果"
        )

    while len(results) < args.count:
        if qq_mode and prefixes:
            # -q / -qn + -dict：
            # 普通模式结果 与 QQ 数字邮箱结果 混合随机输出
            if random.choice([True, False]):
                item = generate_normal_email(prefixes, mail_suffix)
            else:
                item = generate_qq_email(
                    q_length=q_length,
                    weighted=qn_mode
                )

        elif qq_mode:
            # 纯 QQ 数字邮箱模式
            item = generate_qq_email(
                q_length=q_length,
                weighted=qn_mode
            )

        else:
            # 普通模式
            item = generate_normal_email(prefixes, mail_suffix)

        results.add(item)

    output_lines = sorted(results)

    # 仅输出一条，且未指定 -o 时：只打印，不生成文件
    if args.count == 1 and not args.output:
        print(output_lines[0])
        return

    output_path = Path(args.output) if args.output else get_default_output_path()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8") as f:
        f.write("\n".join(output_lines))
        f.write("\n")

    print(f"已生成 {len(output_lines)} 条结果，已输出到文件: {output_path}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"错误: {e}")