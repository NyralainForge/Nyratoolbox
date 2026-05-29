#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
import csv
import ipaddress
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any


Row = dict[str, Any]


@dataclass
class Result:
    title: str
    rows: list[Row]
    notes: list[str] | None = None


def default_output_path() -> Path:
    """默认输出路径。"""
    return Path.home() / "Desktop" / "out.txt"


def output_path(value: str | None) -> Path:
    """解析输出路径。"""
    if value is None or value == "":
        return default_output_path()

    path = Path(value).expanduser()

    if len(path.parts) == 1:
        return Path.home() / "Desktop" / path

    return path


def parse_network(value: str, strict: bool = False) -> ipaddress._BaseNetwork:
    """解析网段。"""
    try:
        return ipaddress.ip_network(value, strict=strict)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc


def parse_interface(value: str) -> ipaddress._BaseInterface:
    """解析接口地址。"""
    try:
        return ipaddress.ip_interface(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc


def parse_address(value: str) -> ipaddress._BaseAddress:
    """解析IP地址。"""
    try:
        return ipaddress.ip_address(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc


def parse_host_requirements(values: list[str]) -> list[tuple[str, int]]:
    """解析主机需求。"""
    requirements: list[tuple[str, int]] = []

    for index, value in enumerate(values, start=1):
        if ":" in value:
            name, count_text = value.split(":", 1)
        elif "=" in value:
            name, count_text = value.split("=", 1)
        else:
            name, count_text = f"net{index}", value

        try:
            count = int(count_text)
        except ValueError as exc:
            raise argparse.ArgumentTypeError(f"主机数量不是整数: {value}") from exc

        if count < 0:
            raise argparse.ArgumentTypeError(f"主机数量不能为负数: {value}")

        requirements.append((name.strip() or f"net{index}", count))

    return requirements


def parse_reserved(values: list[str]) -> list[tuple[ipaddress._BaseAddress, ipaddress._BaseAddress]]:
    """解析保留范围。"""
    ranges = []

    for value in values:
        value = value.strip()
        if not value:
            continue

        if "-" in value:
            start_text, end_text = value.split("-", 1)
            start = parse_address(start_text.strip())
            end = parse_address(end_text.strip())
        else:
            start = end = parse_address(value)

        if start.version != end.version:
            raise argparse.ArgumentTypeError(f"保留地址范围版本不一致: {value}")
        if int(start) > int(end):
            raise argparse.ArgumentTypeError(f"保留地址范围起点大于终点: {value}")

        ranges.append((start, end))

    return ranges


def usable_range(net: ipaddress._BaseNetwork) -> tuple[str, str, int]:
    """计算可用范围。"""
    if net.version == 4:
        if net.prefixlen == 32:
            return str(net.network_address), str(net.network_address), 1
        if net.prefixlen == 31:
            return str(net.network_address), str(net.broadcast_address), 2

        count = max(net.num_addresses - 2, 0)
        if count == 0:
            return "-", "-", 0

        return str(net.network_address + 1), str(net.broadcast_address - 1), count

    if net.prefixlen == 128:
        return str(net.network_address), str(net.network_address), 1
    if net.prefixlen == 127:
        return str(net.network_address), str(net.broadcast_address), 2

    return str(net.network_address), str(net.broadcast_address), net.num_addresses


def ipv4_wildcard(net: ipaddress.IPv4Network) -> str:
    """生成反掩码。"""
    return str(ipaddress.IPv4Address(int(net.hostmask)))


def ipv4_info(interface: ipaddress.IPv4Interface) -> Result:
    """计算IPv4信息。"""
    net = interface.network
    first, last, hosts = usable_range(net)
    rows = [{
        "input_ip": str(interface.ip),
        "prefix": f"/{net.prefixlen}",
        "network": str(net.network_address),
        "broadcast": str(net.broadcast_address),
        "usable_range": f"{first} - {last}" if first != "-" else "-",
        "host_count": hosts,
        "netmask": str(net.netmask),
        "wildcard": ipv4_wildcard(net),
        "hostmask": str(net.hostmask),
        "special": special_note(net),
    }]
    return Result("IPv4 基础计算", rows)


def ipv6_type(addr: ipaddress.IPv6Address) -> str:
    """识别IPv6类型。"""
    if addr.is_multicast:
        return "multicast"
    if addr.is_link_local:
        return "link-local"
    if addr.is_private:
        return "ULA/private"
    if addr.is_loopback:
        return "loopback"
    if addr.is_unspecified:
        return "unspecified"
    if addr.is_global:
        return "global-unicast"
    return "unicast/other"


def ipv6_info(interface: ipaddress.IPv6Interface, child_prefix: int | None) -> Result:
    """计算IPv6信息。"""
    net = interface.network
    first, last, hosts = usable_range(net)
    rows = [{
        "input_ip": str(interface.ip),
        "prefix": f"/{net.prefixlen}",
        "network_prefix": str(net),
        "address_range": f"{first} - {last}",
        "address_count": hosts,
        "address_type": ipv6_type(interface.ip),
        "special": special_note(net),
    }]
    notes = []

    if child_prefix is not None:
        if child_prefix < net.prefixlen or child_prefix > 128:
            raise ValueError("IPv6 子网前缀必须大于等于父网段前缀，且不超过 /128")
        notes.append(f"按 /{child_prefix} 可划分子网数量: {2 ** (child_prefix - net.prefixlen)}")

    return Result("IPv6 基础计算", rows, notes)


def special_note(net: ipaddress._BaseNetwork) -> str:
    """识别特殊前缀。"""
    if net.version == 4 and net.prefixlen == 31:
        return "IPv4 /31 点到点网络，两端地址均可用"
    if net.version == 4 and net.prefixlen == 32:
        return "IPv4 /32 主机路由"
    if net.version == 6 and net.prefixlen == 127:
        return "IPv6 /127 点到点网络"
    if net.version == 6 and net.prefixlen == 128:
        return "IPv6 /128 单地址"
    return ""


def needed_prefix(version: int, hosts: int) -> int:
    """推导最小前缀。"""
    bits = 32 if version == 4 else 128
    if version == 4:
        if hosts <= 1:
            return 32
        if hosts == 2:
            return 31
        needed = hosts + 2
    else:
        if hosts <= 1:
            return 128
        if hosts == 2:
            return 127
        needed = hosts

    host_bits = math.ceil(math.log2(needed))
    return bits - host_bits


def next_aligned_network(start: int, prefix: int, version: int) -> ipaddress._BaseNetwork:
    """获取对齐网段。"""
    bits = 32 if version == 4 else 128
    size = 1 << (bits - prefix)
    aligned = ((start + size - 1) // size) * size
    cls = ipaddress.IPv4Network if version == 4 else ipaddress.IPv6Network
    return cls((aligned, prefix))


def subtract_networks(parent: ipaddress._BaseNetwork, used: list[ipaddress._BaseNetwork]) -> list[ipaddress._BaseNetwork]:
    """扣除已用网段。"""
    free = [parent]

    for subnet in sorted(used, key=lambda item: int(item.network_address)):
        next_free = []
        for chunk in free:
            if subnet.subnet_of(chunk):
                next_free.extend(chunk.address_exclude(subnet))
            else:
                next_free.append(chunk)
        free = next_free

    return sorted(free, key=lambda item: int(item.network_address))


def vlsm(parent: ipaddress._BaseNetwork, requirements: list[tuple[str, int]]) -> Result:
    """执行VLSM划分。"""
    current = int(parent.network_address)
    end = int(parent.broadcast_address)
    allocated: list[tuple[str, int, ipaddress._BaseNetwork]] = []

    for name, hosts in sorted(requirements, key=lambda item: item[1], reverse=True):
        prefix = needed_prefix(parent.version, hosts)
        candidate = next_aligned_network(current, prefix, parent.version)
        if not candidate.subnet_of(parent) or int(candidate.broadcast_address) > end:
            raise ValueError(f"父网段空间不足，无法分配 {name}:{hosts}")

        allocated.append((name, hosts, candidate))
        current = int(candidate.broadcast_address) + 1

    rows = []
    used = []
    for name, hosts, subnet in allocated:
        first, last, usable = usable_range(subnet)
        used.append(subnet)
        rows.append({
            "name": name,
            "required_hosts": hosts,
            "subnet": str(subnet),
            "usable_hosts": usable,
            "range": f"{first} - {last}",
            "network": str(subnet.network_address),
            "broadcast_or_last": str(subnet.broadcast_address),
            "wildcard": ipv4_wildcard(subnet) if subnet.version == 4 else "",
        })

    notes = ["剩余地址空间:"]
    notes.extend(str(item) for item in subtract_networks(parent, used))
    return Result("VLSM 自动划分", rows, notes)


def flsm(parent: ipaddress._BaseNetwork, count: int | None, hosts: int | None) -> Result:
    """执行FLSM划分。"""
    if count is None and hosts is None:
        raise ValueError("FLSM 需要指定 --count 或 --hosts")

    if hosts is not None:
        prefix = needed_prefix(parent.version, hosts)
    else:
        prefix = parent.prefixlen + math.ceil(math.log2(count or 1))

    max_prefix = 32 if parent.version == 4 else 128
    if prefix < parent.prefixlen or prefix > max_prefix:
        raise ValueError("无法在父网段内按指定条件划分")

    subnets = list(parent.subnets(new_prefix=prefix))
    if count is not None:
        subnets = subnets[:count]

    rows = []
    for index, subnet in enumerate(subnets, start=1):
        first, last, usable = usable_range(subnet)
        rows.append({
            "index": index,
            "subnet": str(subnet),
            "usable_hosts": usable,
            "range": f"{first} - {last}",
            "network": str(subnet.network_address),
            "broadcast_or_last": str(subnet.broadcast_address),
            "wildcard": ipv4_wildcard(subnet) if subnet.version == 4 else "",
        })

    return Result("FLSM 等长划分", rows, [f"子网前缀: /{prefix}", f"生成子网数量: {len(rows)}"])


def overlap(networks: list[ipaddress._BaseNetwork]) -> Result:
    """检测网段重叠。"""
    rows = []
    for left_index, left in enumerate(networks):
        for right_index, right in enumerate(networks[left_index + 1:], start=left_index + 2):
            if left.version != right.version:
                relation = "不同 IP 版本"
            elif left == right:
                relation = "冲突: 完全相同"
            elif left.subnet_of(right):
                relation = "包含: 后者包含前者"
            elif right.subnet_of(left):
                relation = "包含: 前者包含后者"
            elif left.overlaps(right):
                relation = "重叠"
            else:
                continue

            rows.append({
                "left_index": left_index + 1,
                "left": str(left),
                "right_index": right_index,
                "right": str(right),
                "relation": relation,
                "conflict_range": conflict_range(left, right),
            })

    if not rows:
        rows.append({"result": "未发现包含、重叠或冲突关系"})

    return Result("子网重叠检测", rows)


def conflict_range(left: ipaddress._BaseNetwork, right: ipaddress._BaseNetwork) -> str:
    """计算冲突范围。"""
    if left.version != right.version or not left.overlaps(right):
        return "-"

    start = max(int(left.network_address), int(right.network_address))
    end = min(int(left.broadcast_address), int(right.broadcast_address))
    cls = ipaddress.IPv4Address if left.version == 4 else ipaddress.IPv6Address
    return f"{cls(start)} - {cls(end)}"


def summarize(networks: list[ipaddress._BaseNetwork], force: bool) -> Result:
    """汇总路由。"""
    if not networks:
        raise ValueError("至少需要一个网段")

    versions = {net.version for net in networks}
    if len(versions) != 1:
        raise ValueError("不能混合汇总 IPv4 与 IPv6 网段")

    collapsed = list(ipaddress.collapse_addresses(networks))
    rows = []
    for item in collapsed:
        rows.append({"summary": str(item), "range": f"{item.network_address} - {item.broadcast_address}"})

    notes = []
    if force:
        first = min(int(item.network_address) for item in networks)
        last = max(int(item.broadcast_address) for item in networks)
        forced = [covering_network(first, last, networks[0].version)]
        notes.append("强制按首尾地址汇总:")
        notes.extend(str(item) for item in forced)
        extra = forced_extra_ranges(networks, forced)
        if extra:
            notes.append("强制汇总会额外包含:")
            notes.extend(extra)
        else:
            notes.append("强制汇总未额外包含地址。")

    return Result("路由汇总", rows, notes)


def covering_network(first: int, last: int, version: int) -> ipaddress._BaseNetwork:
    """计算覆盖网段。"""
    bits = 32 if version == 4 else 128
    diff = first ^ last
    common_bits = bits - diff.bit_length()
    size = 1 << (bits - common_bits)
    network_int = (first // size) * size
    cls = ipaddress.IPv4Network if version == 4 else ipaddress.IPv6Network
    return cls((network_int, common_bits))


def forced_extra_ranges(original: list[ipaddress._BaseNetwork], summaries: list[ipaddress._BaseNetwork]) -> list[str]:
    """找出额外范围。"""
    extras = []
    for summary in summaries:
        free = subtract_networks(summary, [net for net in original if net.subnet_of(summary)])
        extras.extend(str(item) for item in free)
    return extras


def wildcard(args: argparse.Namespace) -> Result:
    """计算ACL通配符。"""
    rows = []

    if args.host:
        addr = ipaddress.IPv4Address(args.host)
        rows.append({
            "type": "single-host",
            "cisco": f"host {addr}",
            "huawei": f"{addr} 0.0.0.0",
            "wildcard": "0.0.0.0",
        })

    if args.network:
        net = ipaddress.IPv4Network(args.network, strict=False)
        wc = ipv4_wildcard(net)
        rows.append({
            "type": "network",
            "network": str(net.network_address),
            "prefix": f"/{net.prefixlen}",
            "cisco": f"{net.network_address} {wc}",
            "huawei": f"{net.network_address} {wc}",
            "wildcard": wc,
        })

    if args.range:
        start = ipaddress.IPv4Address(args.range[0])
        end = ipaddress.IPv4Address(args.range[1])
        if int(start) > int(end):
            raise ValueError("地址范围起点大于终点")
        for net in ipaddress.summarize_address_range(start, end):
            wc = ipv4_wildcard(net)
            rows.append({
                "type": "range-part",
                "range": f"{start} - {end}",
                "network": str(net),
                "cisco": f"{net.network_address} {wc}",
                "huawei": f"{net.network_address} {wc}",
                "wildcard": wc,
            })

    return Result("ACL wildcard 计算", rows)


def dhcp_plan(
    subnet: ipaddress.IPv4Network,
    gateway: ipaddress.IPv4Address,
    reserved: list[tuple[ipaddress._BaseAddress, ipaddress._BaseAddress]],
) -> Result:
    """规划DHCP地址池。"""
    if gateway not in subnet:
        raise ValueError("网关不在子网内")

    first, last, usable = usable_range(subnet)
    if usable == 0:
        raise ValueError("该子网没有可分配主机地址")

    usable_start = ipaddress.IPv4Address(first)
    usable_end = ipaddress.IPv4Address(last)
    excluded = [(gateway, gateway)]

    for start, end in reserved:
        if start.version != 4 or end.version != 4:
            raise ValueError("DHCP 仅支持 IPv4 地址池")
        if start not in subnet or end not in subnet:
            raise ValueError(f"保留地址范围不在子网内: {start}-{end}")
        excluded.append((start, end))

    pools = available_ranges(usable_start, usable_end, excluded)
    rows = [{
        "subnet": str(subnet),
        "gateway": str(gateway),
        "pool_start": str(start),
        "pool_end": str(end),
        "addresses": int(end) - int(start) + 1,
    } for start, end in pools]

    if not rows:
        rows.append({"subnet": str(subnet), "gateway": str(gateway), "result": "无合法可分配地址"})

    notes = ["排除地址:"] + [f"{start} - {end}" for start, end in merge_ranges(excluded)]
    return Result("DHCP 地址池规划", rows, notes)


def merge_ranges(ranges: list[tuple[ipaddress.IPv4Address, ipaddress.IPv4Address]]) -> list[tuple[ipaddress.IPv4Address, ipaddress.IPv4Address]]:
    """合并地址范围。"""
    ordered = sorted(ranges, key=lambda item: int(item[0]))
    merged: list[tuple[ipaddress.IPv4Address, ipaddress.IPv4Address]] = []

    for start, end in ordered:
        if not merged or int(start) > int(merged[-1][1]) + 1:
            merged.append((start, end))
        else:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end, key=int))

    return merged


def available_ranges(
    start: ipaddress.IPv4Address,
    end: ipaddress.IPv4Address,
    excluded: list[tuple[ipaddress.IPv4Address, ipaddress.IPv4Address]],
) -> list[tuple[ipaddress.IPv4Address, ipaddress.IPv4Address]]:
    """计算可分配段。"""
    pools = []
    cursor = int(start)

    for ex_start, ex_end in merge_ranges(excluded):
        if int(ex_end) < cursor:
            continue
        if int(ex_start) > int(end):
            break
        if cursor < int(ex_start):
            pools.append((ipaddress.IPv4Address(cursor), ipaddress.IPv4Address(int(ex_start) - 1)))
        cursor = max(cursor, int(ex_end) + 1)

    if cursor <= int(end):
        pools.append((ipaddress.IPv4Address(cursor), end))

    return pools


def tree_view(parent: ipaddress._BaseNetwork, used: list[ipaddress._BaseNetwork]) -> Result:
    """生成空间树。"""
    rows = [{"level": 0, "type": "parent", "network": str(parent), "addresses": parent.num_addresses}]
    for subnet in sorted(used, key=lambda item: (int(item.network_address), item.prefixlen)):
        rows.append({"level": 1, "type": "used", "network": str(subnet), "addresses": subnet.num_addresses})
    for subnet in subtract_networks(parent, [item for item in used if item.subnet_of(parent)]):
        rows.append({"level": 1, "type": "free", "network": str(subnet), "addresses": subnet.num_addresses})
    return Result("地址空间树状可视化", rows)


def render_tree(result: Result) -> str:
    """渲染文本树。"""
    lines = [f"# {result.title}", ""]
    for row in result.rows:
        prefix = "└── " if row.get("level", 0) else ""
        if row.get("level", 0) == 0:
            lines.append(f"{row['network']} ({row['type']}, {row['addresses']} addresses)")
        else:
            lines.append(f"{prefix}{row['network']} [{row['type']}, {row['addresses']} addresses]")
    return "\n".join(lines)


def markdown_table(result: Result) -> str:
    """渲染Markdown。"""
    if result.title == "地址空间树状可视化":
        body = render_tree(result)
    else:
        keys = []
        for row in result.rows:
            for key in row:
                if key not in keys:
                    keys.append(key)

        lines = [f"# {result.title}", ""]
        if keys:
            lines.append("| " + " | ".join(keys) + " |")
            lines.append("| " + " | ".join("---" for _ in keys) + " |")
            for row in result.rows:
                values = [str(row.get(key, "")).replace("\n", "<br>") for key in keys]
                lines.append("| " + " | ".join(values) + " |")
        body = "\n".join(lines)

    if result.notes:
        body += "\n\n## Notes\n\n" + "\n".join(f"- {note}" for note in result.notes)

    return body + "\n"


def csv_text(result: Result) -> str:
    """渲染CSV。"""
    import io

    keys = []
    for row in result.rows:
        for key in row:
            if key not in keys:
                keys.append(key)

    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=keys, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(result.rows)

    if result.notes:
        buffer.write("\nnotes\n")
        for note in result.notes:
            buffer.write(f"{note}\n")

    return buffer.getvalue()


def render(result: Result, fmt: str) -> str:
    """按格式渲染。"""
    if fmt == "csv":
        return csv_text(result)
    return markdown_table(result)


def output_format(path: Path, requested_format: str | None) -> str:
    """选择输出格式。"""
    if requested_format is not None:
        return requested_format

    # 未指定格式时按文件扩展名推导。
    suffix = path.suffix.lower()

    if suffix == ".csv":
        return "csv"

    return "md"


def result_keys(result: Result) -> list[str]:
    """收集结果字段。"""
    keys = []
    for row in result.rows:
        for key in row:
            if key not in keys:
                keys.append(key)
    return keys


def print_result(result: Result, fallback_text: str) -> None:
    """打印终端结果。"""
    try:
        from rich import box
        from rich.console import Console
        from rich.panel import Panel
        from rich.table import Table
        from rich.text import Text
        from rich.tree import Tree
    except ImportError:
        print(fallback_text, end="")
        return

    console = Console()

    if result.title == "地址空间树状可视化":
        print_rich_tree(console, Tree, result)
    else:
        keys = result_keys(result)
        table = Table(
            title=result.title,
            box=box.ROUNDED,
            header_style="bold cyan",
            show_lines=any("\n" in str(value) for row in result.rows for value in row.values()),
        )

        for key in keys:
            justify = "right" if all(is_number_like(row.get(key, "")) for row in result.rows) else "left"
            table.add_column(key, overflow="fold", justify=justify)

        for row in result.rows:
            table.add_row(*[str(row.get(key, "")) for key in keys])

        console.print(table)

    if result.notes:
        notes = Text()
        for index, note in enumerate(result.notes):
            if index:
                notes.append("\n")
            notes.append(f"- {note}")
        console.print(Panel(notes, title="Notes", border_style="yellow"))


def print_rich_tree(console: Any, tree_class: Any, result: Result) -> None:
    """打印漂亮树。"""
    parent = result.rows[0] if result.rows else None
    if not parent:
        console.print(result.title)
        return

    root = tree_class(f"[bold cyan]{parent['network']}[/] [dim]({parent['type']}, {parent['addresses']} addresses)[/]")
    for row in result.rows[1:]:
        style = "green" if row.get("type") == "free" else "magenta"
        root.add(f"[{style}]{row['network']}[/] [dim]({row['type']}, {row['addresses']} addresses)[/]")

    console.print(Panel(root, title=result.title, border_style="cyan"))


def is_number_like(value: Any) -> bool:
    """判断数字文本。"""
    if isinstance(value, (int, float)):
        return True

    text = str(value)
    return text.isdigit()


def write_output(path: Path, text: str) -> None:
    """写入输出文件。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    """构建参数解析。"""
    output_parent = argparse.ArgumentParser(add_help=False)
    output_parent.add_argument("-p", "--print", dest="print_result", action="store_true", default=argparse.SUPPRESS, help="将结果打印到屏幕")
    output_parent.add_argument("-o", "--output", nargs="?", const="", default=argparse.SUPPRESS, help="输出文件路径；只写 -o 时默认输出到桌面 out.txt")
    output_parent.add_argument("--format", choices=["md", "csv"], default=argparse.SUPPRESS, help="指定输出格式；未指定时按输出文件扩展名推导")

    parser = argparse.ArgumentParser(description="Subnetting CLI: IPv4/IPv6/VLSM/FLSM/ACL/DHCP planner")
    parser.add_argument("-p", "--print", dest="print_result", action="store_true", help="将结果打印到屏幕")
    parser.add_argument("-o", "--output", nargs="?", const="", help="输出文件路径；只写 -o 时默认输出到桌面 out.txt")
    parser.add_argument("--format", choices=["md", "csv"], help="指定输出格式；未指定时按输出文件扩展名推导")

    subparsers = parser.add_subparsers(dest="command", required=True)

    ipv4_parser = subparsers.add_parser("ipv4", parents=[output_parent], help="IPv4 基础计算")
    ipv4_parser.add_argument("address", type=parse_interface, help="IPv4 地址/CIDR，例如 192.168.1.10/24")
    ipv4_parser.add_argument("--mask", help="子网掩码，例如 255.255.255.0")

    ipv6_parser = subparsers.add_parser("ipv6", parents=[output_parent], help="IPv6 基础计算")
    ipv6_parser.add_argument("address", type=parse_interface, help="IPv6 地址/前缀，例如 fd00::1/64")
    ipv6_parser.add_argument("--child-prefix", type=int, help="用于计算可划分子网数量的目标前缀")

    vlsm_parser = subparsers.add_parser("vlsm", parents=[output_parent], help="VLSM 自动划分")
    vlsm_parser.add_argument("parent", type=parse_network)
    vlsm_parser.add_argument("hosts", nargs="+", help="业务名:主机数，例如 office:120 guest:50")

    flsm_parser = subparsers.add_parser("flsm", parents=[output_parent], help="FLSM 等长划分")
    flsm_parser.add_argument("parent", type=parse_network)
    flsm_parser.add_argument("--count", type=int, help="平均划分的子网数量")
    flsm_parser.add_argument("--hosts", type=int, help="每个子网需要的主机数量")

    overlap_parser = subparsers.add_parser("overlap", parents=[output_parent], help="子网重叠检测")
    overlap_parser.add_argument("networks", nargs="+", type=parse_network)

    summarize_parser = subparsers.add_parser("summarize", parents=[output_parent], help="路由汇总")
    summarize_parser.add_argument("networks", nargs="+", type=parse_network)
    summarize_parser.add_argument("--force", action="store_true", help="按首尾地址强制汇总并提示额外范围")

    wildcard_parser = subparsers.add_parser("wildcard", parents=[output_parent], help="ACL wildcard 计算")
    wildcard_parser.add_argument("--host", help="单主机 IPv4 地址")
    wildcard_parser.add_argument("--network", help="IPv4 网段，例如 192.168.1.0/24")
    wildcard_parser.add_argument("--range", nargs=2, metavar=("START", "END"), help="IPv4 地址范围")

    dhcp_parser = subparsers.add_parser("dhcp", parents=[output_parent], help="DHCP 地址池规划")
    dhcp_parser.add_argument("subnet", type=lambda value: ipaddress.IPv4Network(value, strict=False))
    dhcp_parser.add_argument("--gateway", required=True, type=ipaddress.IPv4Address)
    dhcp_parser.add_argument("--reserve", action="append", default=[], help="保留地址或范围，可重复，例如 192.168.1.10-192.168.1.20")

    tree_parser = subparsers.add_parser("tree", parents=[output_parent], help="地址空间树状可视化")
    tree_parser.add_argument("parent", type=parse_network)
    tree_parser.add_argument("used", nargs="*", type=parse_network)

    return parser


def run(args: argparse.Namespace) -> Result:
    """分发子命令。"""
    if args.command == "ipv4":
        if args.address.version != 4:
            raise ValueError("ipv4 子命令只接受 IPv4 地址")
        interface = args.address
        if args.mask:
            interface = ipaddress.IPv4Interface(f"{interface.ip}/{args.mask}")
        return ipv4_info(interface)

    if args.command == "ipv6":
        if args.address.version != 6:
            raise ValueError("ipv6 子命令只接受 IPv6 地址")
        return ipv6_info(args.address, args.child_prefix)

    if args.command == "vlsm":
        return vlsm(args.parent, parse_host_requirements(args.hosts))

    if args.command == "flsm":
        return flsm(args.parent, args.count, args.hosts)

    if args.command == "overlap":
        return overlap(args.networks)

    if args.command == "summarize":
        return summarize(args.networks, args.force)

    if args.command == "wildcard":
        if not args.host and not args.network and not args.range:
            raise ValueError("wildcard 至少需要 --host、--network 或 --range 之一")
        return wildcard(args)

    if args.command == "dhcp":
        return dhcp_plan(args.subnet, args.gateway, parse_reserved(args.reserve))

    if args.command == "tree":
        return tree_view(args.parent, args.used)

    raise ValueError(f"未知命令: {args.command}")


def main() -> int:
    """程序入口。"""
    parser = build_parser()
    args = parser.parse_args()

    try:
        result = run(args)
        screen_text = render(result, args.format or "md")

        if args.print_result or not args.output:
            print_result(result, screen_text)

        if args.output is not None:
            path = output_path(args.output)
            file_text = render(result, output_format(path, args.format))
            write_output(path, file_text)
            if not args.print_result:
                print(f"已输出到文件: {path}")

        return 0
    except (ValueError, argparse.ArgumentTypeError) as exc:
        parser.error(str(exc))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
