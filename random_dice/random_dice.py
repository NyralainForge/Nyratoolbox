#!/usr/bin/env python3
"""Standalone dice CLI and shared web engine. Python 3.9+, standard library only.

Examples:
  python3 random_dice.py
  python3 random_dice.py '2D6+1D4' --modifier 3
  python3 random_dice.py '2[-3,8]+1D20' --json
  python3 random_dice.py '1D20' --total-only
"""

import argparse
import json
import re
import sys
from secrets import randbelow

PRESETS = {f"d{sides}": f"1D{sides}" for sides in (4, 6, 8, 10, 12, 20)}
PRESETS.update({"2d6": "2D6", "2d6d4": "2D6+1D4"})

def generate_random_numbers(form: dict[str, str]) -> list[int]:
    values = []
    for name, label in (("minimum", "最小值"), ("maximum", "最大值"), ("count", "生成个数")):
        value = form.get(name, "").strip()
        if len(value) > 15 or re.fullmatch(r"[+-]?[0-9]+", value) is None:
            raise ValueError(f"{label}必须是整数")
        values.append(int(value))
    minimum, maximum, count = values
    if not (-10**12 <= minimum <= maximum <= 10**12):
        raise ValueError("最小值不能大于最大值，且两端必须在 ±1,000,000,000,000 内")
    if not 1 <= count <= 10000:
        raise ValueError("生成个数必须在 1 至 10,000 之间")
    if form.get("sum", "") not in ("", "yes"):
        raise ValueError("求和选项无效")
    return [minimum + randbelow(maximum - minimum + 1) for _ in range(count)]


def generate_random_result(form: dict[str, str]):
    modifier_text = form.get("modifier", "0").strip()
    if re.fullmatch(r"[+-]?[0-9]{1,13}", modifier_text) is None:
        raise ValueError("固定加值必须是整数")
    modifier = int(modifier_text)
    if abs(modifier) > 10**12:
        raise ValueError("固定加值必须在 ±1,000,000,000,000 内")
    expression = re.sub(r"\s+", "", form.get("expression", ""))
    if not expression:
        if "expression" in form:
            raise ValueError("请输入骰子组合，例如 1D10 或 2[3,8]")
        return generate_random_numbers(form), None, modifier
    if len(expression) > 512:
        raise ValueError("组合表达式过长")
    terms = expression.split("+")
    if len(terms) > 20:
        raise ValueError("每次最多组合 20 组")
    specs = []
    total_count = 0
    for term in terms:
        dice = re.fullmatch(r"([0-9]{1,5})[dD]([0-9]{1,13})", term)
        custom = re.fullmatch(r"([0-9]{1,5})\[(-?[0-9]{1,13}),(-?[0-9]{1,13})\]", term)
        if dice:
            count, maximum = map(int, dice.groups())
            minimum = 1
            label = f"{count}D{maximum}"
        elif custom:
            count, minimum, maximum = map(int, custom.groups())
            label = f"{count}[{minimum},{maximum}]"
        else:
            raise ValueError("组合格式无效，请使用 2D6+1D4 或 2[3,8]+1[-2,4]")
        total_count += count
        if count < 1 or total_count > 10000:
            raise ValueError("每组至少 1 个，合计最多生成 10,000 个随机数")
        if not -10**12 <= minimum <= maximum <= 10**12:
            raise ValueError("每组范围必须有序且在 ±1,000,000,000,000 内")
        specs.append((label, minimum, maximum, count))
    groups = []
    numbers = []
    for label, minimum, maximum, count in specs:
        values = [minimum + randbelow(maximum - minimum + 1) for _ in range(count)]
        groups.append((label, values))
        numbers.extend(values)
    return numbers, groups, modifier


def roll(expression: str = "1D10", modifier: str = "0") -> dict:
    """Return per-group values, subtotals and a total with modifier added once."""
    numbers, groups, addition = generate_random_result({
        "expression": expression, "modifier": str(modifier),
    })
    return {
        "expression": "+".join(label for label, _ in groups),
        "groups": [{"expression": label, "values": values, "subtotal": sum(values)}
                   for label, values in groups],
        "count": len(numbers),
        "subtotal": sum(numbers),
        "modifier": addition,
        "total": sum(numbers) + addition,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="随机数 / 组合骰子 CLI，与网页使用同一计算逻辑。默认 1D10，固定加值默认 0。",
        epilog="表达式最多 20 组、合计 10000 个；范围与固定加值限制 ±10^12。含 + 或 [] 的表达式请加引号。",
    )
    parser.add_argument("expression", nargs="?", default="1D10", help="如 '2D6+1D4' 或 '2[-3,8]+1D20'")
    parser.add_argument("-m", "--modifier", default="0", help="固定加值，只加一次，可为负数")
    output = parser.add_mutually_exclusive_group()
    output.add_argument("--json", action="store_true", help="输出 JSON，便于其他程序读取")
    output.add_argument("--total-only", action="store_true", help="只输出最终总和")
    args = parser.parse_args(argv)
    try:
        result = roll(args.expression, args.modifier)
    except ValueError as exc:
        parser.error(str(exc))
    except KeyboardInterrupt:
        print("\n已取消。", file=sys.stderr)
        return 130
    if args.json:
        print(json.dumps(result, ensure_ascii=False))
    elif args.total_only:
        print(result["total"])
    else:
        print("组合：" + result["expression"])
        for group in result["groups"]:
            print(f"{group['expression']}: " + ", ".join(map(str, group["values"])) + f"  小计 {group['subtotal']}")
        print(f"随机数合计：{result['subtotal']}")
        print(f"固定加值：{result['modifier']:+d}（仅加一次）")
        print(f"总和：{result['total']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
