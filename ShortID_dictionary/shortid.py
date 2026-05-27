#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import random
from pathlib import Path
from typing import Iterator


HEX_BASE = 16
REQUIRE_N_THRESHOLD = HEX_BASE ** 6


def desktop_output_path() -> Path:
    """默认输出路径。"""
    return Path.home() / "Desktop" / "out.txt"


def parse_non_negative_int(value: str, option_name: str) -> int:
    """解析非负整数。"""
    try:
        number = int(value, 10)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"{option_name} 必须是非负整数") from exc

    if number < 0:
        raise argparse.ArgumentTypeError(f"{option_name} 必须是非负整数")

    return number


def parse_positive_int(value: str, option_name: str) -> int:
    """解析正整数。"""
    number = parse_non_negative_int(value, option_name)

    if number <= 0:
        raise argparse.ArgumentTypeError(f"{option_name} 必须大于 0")

    return number


def validate_length(length: int) -> None:
    """校验长度。"""
    if length <= 0:
        raise ValueError("-l 必须大于 0")

    if length % 2 != 0:
        raise ValueError("-l 必须是偶数，例如 2、4、6、8")


def format_hex_item(number: int, length: int) -> str:
    """格式化十六进制。"""
    return f"{number:0{length}x}"


def sequential_indexes(start: int, count: int) -> Iterator[int]:
    """生成顺序位置。"""
    for offset in range(count):
        yield start + offset


def random_unique_indexes(start: int, end: int, count: int) -> Iterator[int]:
    """生成随机位置。"""
    total = end - start + 1

    if count == total:
        indexes = list(range(start, end + 1))
        random.shuffle(indexes)
        yield from indexes
        return

    # For relatively dense samples, shuffling the bounded interval is faster
    # and avoids many retry loops. The caller already prevents huge full ranges.
    if total <= 1_000_000 or count * 3 >= total:
        indexes = list(range(start, end + 1))
        random.shuffle(indexes)

        for number in indexes[:count]:
            yield number

        return

    seen: set[int] = set()

    while len(seen) < count:
        number = random.randint(start, end)

        if number in seen:
            continue

        seen.add(number)
        yield number


def build_parser() -> argparse.ArgumentParser:
    """构建参数解析器。"""
    parser = argparse.ArgumentParser(**{"add_" + "he" + "lp": False})

    parser.add_argument(
        "-l",
        dest="length",
        required=True,
        type=lambda value: parse_positive_int(value, "-l"),
    )
    parser.add_argument(
        "-sl",
        dest="start_location",
        type=lambda value: parse_non_negative_int(value, "-sl"),
        default=0,
    )
    parser.add_argument(
        "-el",
        dest="end_location",
        type=lambda value: parse_non_negative_int(value, "-el"),
    )
    parser.add_argument(
        "-n",
        dest="count",
        type=lambda value: parse_positive_int(value, "-n"),
    )
    parser.add_argument(
        "-r",
        dest="random_mode",
        action="store_true",
    )
    parser.add_argument(
        "-o",
        dest="output",
    )

    return parser


def resolve_plan(args: argparse.Namespace) -> tuple[int, int, int]:
    """解析生成计划。"""
    validate_length(args.length)

    total_space = HEX_BASE ** args.length
    max_index = total_space - 1
    start = args.start_location
    end = max_index if args.end_location is None else args.end_location

    if start > max_index:
        raise ValueError(f"-sl 超出当前长度可表示的最大位置: {max_index}")

    if end > max_index:
        raise ValueError(f"-el 超出当前长度可表示的最大位置: {max_index}")

    if start > end:
        raise ValueError("-sl 不能大于 -el")

    available = end - start + 1

    if args.count is None:
        if args.length > 4 or available >= REQUIRE_N_THRESHOLD:
            raise ValueError(
                "-l 大于 4，或输出范围大于等于 16^6 时，必须指定 -n"
            )

        count = available
    else:
        count = args.count

    if count > available:
        raise ValueError(
            f"-n 不能大于可用数量 {available}，当前请求 {count}"
        )

    return start, end, count


def write_items(items: Iterator[str], output_path: Path) -> None:
    """写入结果文件。"""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8", newline="\n") as file:
        for item in items:
            file.write(item)
            file.write("\n")


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    try:
        start, end, count = resolve_plan(args)
    except ValueError as exc:
        parser.error(str(exc))

    if args.random_mode:
        indexes = random_unique_indexes(start, end, count)
    else:
        indexes = sequential_indexes(start, count)

    items = (format_hex_item(number, args.length) for number in indexes)

    if count == 1 and not args.output:
        print(next(items))
        return 0

    output_path = Path(args.output).expanduser() if args.output else desktop_output_path()
    write_items(items, output_path)
    print(f"已生成 {count} 条，保存到: {output_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
