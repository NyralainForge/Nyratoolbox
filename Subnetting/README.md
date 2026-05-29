# Subnetting CLI

一个纯命令行子网规划工具，支持 IPv4 / IPv6 基础计算、VLSM / FLSM 划分、重叠检测、路由汇总、ACL wildcard、DHCP 地址池和地址空间树状展示。

默认仅使用 Python 标准库，无需安装依赖。如果本地已安装 `rich`，屏幕输出会自动使用漂亮表格；未安装时会自动退回普通 Markdown 文本输出，程序不会崩溃。

## 全局参数

```text
-p, --print          将结果打印在屏幕上
-o [OUTPUT]          输出到文件；只填写 -o 时默认输出到 ~/Desktop/out.txt
--format md|csv      指定输出格式；未指定时按输出文件扩展名推导
```

未指定 `-o` 时，结果默认打印到屏幕。指定 `-o` 且不加 `-p` 时，只显示输出路径。

`rich` 只影响终端屏幕显示，不参与文件写入。未指定 `--format` 时，输出到 `.txt` 文件默认写入 Markdown 格式，输出到 `.csv` 文件默认写入逗号分隔值文件格式。指定 `--format` 时，以指定格式为准。

## 参数

### ipv4

IPv4 基础计算。输入一个 IPv4 地址/CIDR，输出该地址所在网段的关键字段，适合检查网络地址、广播地址、可用主机范围、可用主机数量、子网掩码和 ACL wildcard 反掩码。

```text
address          IPv4 地址/CIDR，例如 192.168.1.10/24
--mask MASK      子网掩码，例如 255.255.255.0；会覆盖 address 中的前缀
```

输出字段：

```text
input_ip         输入 IP
prefix           前缀长度
network          网络地址
broadcast        广播地址
usable_range     可用主机范围
host_count       可用主机数量
netmask          子网掩码
wildcard         ACL wildcard 反掩码
hostmask         hostmask
special          特殊说明
```

示例：

```bash
python3 subnetting.py ipv4 192.168.1.10/24
```

典型结果包含：

```text
input_ip: 192.168.1.10
prefix: /24
network: 192.168.1.0
broadcast: 192.168.1.255
usable_range: 192.168.1.1 - 192.168.1.254
host_count: 254
netmask: 255.255.255.0
wildcard: 0.0.0.255
hostmask: 0.0.0.255
```

也可以用 `--mask` 单独指定子网掩码：

```bash
python3 subnetting.py ipv4 192.168.1.10/24 --mask 255.255.255.128
```

这里 `--mask` 会覆盖原来的 `/24`，相当于重新计算 `192.168.1.10/255.255.255.128`，也就是 `/25`。

### ipv6

IPv6 基础计算。输入 IPv6 地址/前缀，输出网络前缀、地址范围、地址数量和地址类型，适合做 IPv6 地址规划、前缀核对和地址类型识别。

```text
address                 IPv6 地址/前缀，例如 fd00::1/64
--child-prefix PREFIX   目标子网前缀，用于计算可划分子网数量
```

输出字段：

```text
input_ip         输入 IP
prefix           前缀长度
network_prefix   网络前缀
address_range    地址范围
address_count    地址数量
address_type     地址类型
special          特殊说明
```

示例：

```bash
python3 subnetting.py ipv6 fd00:aabb::1/64
```

典型结果包含：

```text
input_ip: fd00:aabb::1
prefix: /64
network_prefix: fd00:aabb::/64
address_range: fd00:aabb:: - fd00:aabb::ffff:ffff:ffff:ffff
address_count: 18446744073709551616
address_type: ULA/private
```

也可以计算某个父前缀可以划分出多少个子网：

```bash
python3 subnetting.py ipv6 fd00:aabb::1/48 --child-prefix 64
```

Notes 中会显示：

```text
按 /64 可划分子网数量: 65536
```

计算逻辑是 `2^(64 - 48) = 65536`。

IPv6 地址类型识别逻辑：

```text
multicast        组播地址
link-local       链路本地地址
ULA/private      ULA 或 Python ipaddress 归类为 private 的地址
loopback         环回地址
unspecified      未指定地址
global-unicast   全局单播地址
unicast/other    其他单播地址
```

小提醒：Python `ipaddress` 的 `is_private` 不只覆盖 ULA，有些特殊地址也可能被归为 private，所以这里显示为 `ULA/private`，是一个宽泛判断。

### vlsm

VLSM 自动划分。根据不同业务所需主机数量，在父网段中自动分配不同大小的子网。适合办公网、访客网、服务器区、点到点链路等规模不同的地址规划。

```text
parent           父网段，例如 192.168.10.0/24
hosts            业务名:主机数 或 业务名=主机数，可填写多个，例如 office:120 guest:50
```

示例：

```bash
python3 subnetting.py vlsm 192.168.10.0/24 office:120 guest:50 server:20 p2p:2
```

程序会先把需求按主机数从大到小排序：

```text
office 120
guest  50
server 20
p2p    2
```

然后自动分配最合适前缀：

```text
office -> /25
guest  -> /26
server -> /27
p2p    -> /31
```

输出字段：

```text
name              业务名称
required_hosts    需求主机数
subnet            分配到的子网
usable_hosts      可用主机数
range             可用地址范围
network           网络地址
broadcast_or_last 广播地址或最后地址
wildcard          IPv4 ACL wildcard
```

典型分配结果：

```text
office  192.168.10.0/25
guest   192.168.10.128/26
server  192.168.10.192/27
p2p     192.168.10.224/31
```

最后 Notes 会显示剩余地址空间，方便继续规划或检查浪费情况。

### flsm

FLSM 等长划分。FLSM 是 Fixed Length Subnet Mask，表示所有子网长度一样。适合所有 VLAN、分支或实验网段都需要相同规模地址池的场景。

```text
parent           父网段，例如 10.0.0.0/24
--count COUNT    平均划分的子网数量
--hosts HOSTS    每个子网需要的主机数量，用于自动推导前缀
```

按子网数量划分：

```bash
python3 subnetting.py flsm 192.168.1.0/24 --count 4
```

程序会计算 `/24 + log2(4) = /26`，得到：

```text
192.168.1.0/26
192.168.1.64/26
192.168.1.128/26
192.168.1.192/26
```

按每个子网需要的主机数划分：

```bash
python3 subnetting.py flsm 192.168.1.0/24 --hosts 50
```

IPv4 中 50 台主机需要加上网络地址和广播地址，也就是至少 52 个地址；最小 2 的幂是 64，所以会推导为 `/26`，并生成多个 `/26` 子网。

如果同时指定 `--hosts` 和 `--count`，程序会先按 `--hosts` 推导前缀，再只显示前 `--count` 个子网。

### overlap

网段重叠检测。用于检测多个网段之间是否完全相同、互相包含、部分重叠，或属于不同 IP 版本。适合检查静态路由、OSPF 汇总、ACL 范围和 DHCP 地址池是否撞车。

```text
networks         需要检查的网段列表，可填写多个
```

示例：

```bash
python3 subnetting.py overlap 192.168.1.0/24 192.168.1.128/25 10.0.0.0/8
```

程序会发现 `192.168.1.128/25` 被 `192.168.1.0/24` 包含，并输出冲突地址范围：

```text
192.168.1.128 - 192.168.1.255
```

如果没有发现问题，会输出：

```text
未发现包含、重叠或冲突关系
```

### summarize

路由汇总。用于对多个网段做 CIDR 汇总，适合整理静态路由、优化路由表、准备汇总路由公告，或检查多个连续网段能否聚合成更少的路由。

```text
networks         需要汇总的网段列表，可填写多个
--force          按首尾地址强制汇总，并提示额外包含的地址范围
```

安全汇总示例：

```bash
python3 subnetting.py summarize 192.168.0.0/24 192.168.1.0/24 192.168.2.0/24 192.168.3.0/24
```

会汇总成：

```text
192.168.0.0/22
```

默认使用 `ipaddress.collapse_addresses(networks)`，只做合理、安全、不额外包含地址的汇总。

强制汇总示例：

```bash
python3 subnetting.py summarize 192.168.0.0/24 192.168.2.0/24 --force
```

正常安全汇总可能仍然分开显示：

```text
192.168.0.0/24
192.168.2.0/24
```

加 `--force` 后，程序会按首尾地址计算一个能覆盖全部范围的最小大网段，并列出强制汇总额外包含的地址空间。这个提示可以帮助避免为了少写一条路由，把不属于自己的网段也汇总进去。

### wildcard

ACL wildcard 反掩码计算。用于计算 Cisco / Huawei ACL 中常见的 wildcard 表达，支持单主机、网段和任意地址范围。

```text
--host IP                单主机 IPv4 地址
--network NETWORK        IPv4 网段，例如 192.168.1.0/24
--range START END        IPv4 地址范围，会自动拆分为最小 CIDR 片段
```

单主机：

```bash
python3 subnetting.py wildcard --host 192.168.1.10
```

输出类似：

```text
type: single-host
cisco: host 192.168.1.10
huawei: 192.168.1.10 0.0.0.0
wildcard: 0.0.0.0
```

网段：

```bash
python3 subnetting.py wildcard --network 192.168.1.0/24
```

输出类似：

```text
cisco: 192.168.1.0 0.0.0.255
huawei: 192.168.1.0 0.0.0.255
wildcard: 0.0.0.255
```

地址范围：

```bash
python3 subnetting.py wildcard --range 192.168.1.10 192.168.1.30
```

程序会用 `ipaddress.summarize_address_range(start, end)` 把任意地址范围拆成最少数量的 CIDR 段，再输出每一段对应的 wildcard。这个功能适合处理范围不是标准网段的 ACL。

### dhcp

DHCP 地址池规划。根据子网、网关和保留地址，计算 DHCP 可分配地址池。适合在写 DHCP 配置前，先排除网关、服务器、打印机和固定地址。

```text
subnet                   DHCP 所属 IPv4 子网
--gateway IP             网关地址，必须在 subnet 内
--reserve VALUE          保留地址或地址范围，可重复使用，例如 192.168.1.10-192.168.1.20
```

基础示例：

```bash
python3 subnetting.py dhcp 192.168.1.0/24 --gateway 192.168.1.1
```

输出类似：

```text
subnet: 192.168.1.0/24
gateway: 192.168.1.1
pool_start: 192.168.1.2
pool_end: 192.168.1.254
addresses: 253
```

因为 `192.168.1.0` 是网络地址，`192.168.1.255` 是广播地址，`192.168.1.1` 是网关并会被排除。

带保留地址：

```bash
python3 subnetting.py dhcp 192.168.1.0/24 \
  --gateway 192.168.1.1 \
  --reserve 192.168.1.10-192.168.1.20 \
  --reserve 192.168.1.100
```

程序会自动排除：

```text
192.168.1.1
192.168.1.10 - 192.168.1.20
192.168.1.100
```

然后把剩余地址池拆成几段：

```text
192.168.1.2 - 192.168.1.9
192.168.1.21 - 192.168.1.99
192.168.1.101 - 192.168.1.254
```

### tree

地址空间树状可视化。展示一个父网段中哪些子网已被使用，哪些空间仍然空闲。适合配合 VLSM 的剩余空间结果，判断地址池还剩多少。

```text
parent           父网段
used             已使用的子网列表，可为空或填写多个
```

```bash
python3 subnetting.py tree 192.168.1.0/24 192.168.1.0/26 192.168.1.128/25
```

输出类似：

```text
# 地址空间树状可视化

192.168.1.0/24 (parent, 256 addresses)
└── 192.168.1.0/26 [used, 64 addresses]
└── 192.168.1.128/25 [used, 128 addresses]
└── 192.168.1.64/26 [free, 64 addresses]
```

如果安装了 `rich`，终端会显示成彩色树状结构。

### 特殊前缀处理

程序对一些特殊前缀做了单独处理，避免把点到点链路和主机路由算错。

```text
IPv4 /31     点到点网络，两端地址均可用
IPv4 /32     主机路由，只有一个地址
IPv6 /127    点到点网络，两个地址都可用
IPv6 /128    单地址
```

示例：

```bash
python3 subnetting.py ipv4 10.0.0.0/31
```

会认为两个地址都可用：

```text
usable_range: 10.0.0.0 - 10.0.0.1
host_count: 2
```

### 子命令总览

```text
ipv4        IPv4 地址、掩码、广播、反掩码、可用范围计算
ipv6        IPv6 前缀、地址范围、地址类型、子前缀数量计算
vlsm        按不同主机需求自动划分变长子网
flsm        按固定长度划分等长子网
overlap     检测多个网段是否重叠或包含
summarize   路由汇总
wildcard    ACL wildcard 计算
dhcp        DHCP 地址池规划
tree        地址空间树状展示
```

### 常用命令速查

```bash
# IPv4 基础计算
python3 subnetting.py ipv4 192.168.1.10/24

# IPv4 使用独立子网掩码
python3 subnetting.py ipv4 192.168.1.10/24 --mask 255.255.255.128

# IPv6 基础计算
python3 subnetting.py ipv6 fd00:aabb::1/64

# IPv6 计算 /48 能分多少个 /64
python3 subnetting.py ipv6 fd00:aabb::1/48 --child-prefix 64

# VLSM 自动划分
python3 subnetting.py vlsm 192.168.10.0/24 office:120 guest:50 server:20 p2p:2

# FLSM 按数量划分
python3 subnetting.py flsm 192.168.1.0/24 --count 4

# FLSM 按主机数划分
python3 subnetting.py flsm 192.168.1.0/24 --hosts 50

# 检测网段重叠
python3 subnetting.py overlap 192.168.1.0/24 192.168.1.128/25 10.0.0.0/8

# 路由汇总
python3 subnetting.py summarize 192.168.0.0/24 192.168.1.0/24

# 强制路由汇总并显示额外包含范围
python3 subnetting.py summarize 192.168.0.0/24 192.168.2.0/24 --force

# ACL 单主机 wildcard
python3 subnetting.py wildcard --host 192.168.1.10

# ACL 网段 wildcard
python3 subnetting.py wildcard --network 192.168.1.0/24

# ACL 地址范围拆分
python3 subnetting.py wildcard --range 192.168.1.10 192.168.1.30

# DHCP 地址池规划
python3 subnetting.py dhcp 192.168.1.0/24 --gateway 192.168.1.1

# DHCP 地址池规划，带保留地址
python3 subnetting.py dhcp 192.168.1.0/24 --gateway 192.168.1.1 --reserve 192.168.1.10-192.168.1.20

# 地址空间树
python3 subnetting.py tree 192.168.1.0/24 192.168.1.0/26 192.168.1.128/25

# 输出 Markdown 文件
python3 subnetting.py ipv4 192.168.1.10/24 -o result.md

# 输出 CSV 文件
python3 subnetting.py ipv4 192.168.1.10/24 -o result.csv

# 打印并输出文件
python3 subnetting.py ipv4 192.168.1.10/24 -p -o result.md
```

## 注意

- 本工具面向合法的网络规划、教学演示、配置草稿生成和文档整理。
- IPv4 主机数量按常规可用地址计算，特殊处理 `/31` 与 `/32`。
- IPv6 地址范围按网络内地址空间展示，特殊处理 `/127` 与 `/128`。
