# Subnetting CLI

一个纯命令行子网规划工具，支持 IPv4 / IPv6 基础计算、VLSM / FLSM 划分、重叠检测、路由汇总、ACL wildcard、DHCP 地址池和地址空间树状展示。

默认仅使用 Python 标准库，无需安装依赖。如果本地已安装 `rich`，屏幕输出会自动使用漂亮表格；未安装时会自动退回普通 Markdown 文本输出，程序不会崩溃。

## 文件

```text
Subnetting/
├── subnetting.py
└── README.md
```

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

用于 IPv4 地址基础计算。适合检查某个 IPv4 地址属于哪个网段、可用地址范围是多少、广播地址是什么，以及写 ACL 或网络文档时需要掩码和反掩码的场景。

```text
address          IPv4 地址/CIDR，例如 192.168.1.10/24
--mask MASK      子网掩码，例如 255.255.255.0；会覆盖 address 中的前缀
```

`address` 可以直接写成 `IP/前缀`。如果现场只拿到传统子网掩码，可以用 `--mask` 指定掩码，程序会按该掩码重新计算网络信息。

### ipv6

用于 IPv6 地址和前缀基础计算。适合确认 IPv6 网络前缀、地址范围、地址类型，以及估算从一个父前缀继续划分子网的数量。

```text
address                 IPv6 地址/前缀，例如 fd00::1/64
--child-prefix PREFIX   目标子网前缀，用于计算可划分子网数量
```

`address` 用来指定 IPv6 地址和当前前缀。`--child-prefix` 用在规划 IPv6 子网时，例如从 `/48` 规划 `/64` 或从 `/64` 规划 `/80`，程序会输出可划分子网数量。

### vlsm

用于 VLSM 不等长子网划分。适合不同部门、业务区、楼层或 VLAN 需要不同主机数量时，从一个父网段中自动按需求分配地址空间。

```text
parent           父网段，例如 192.168.10.0/24
hosts            业务名:主机数 或 业务名=主机数，可填写多个，例如 office:120 guest:50
```

`parent` 是可分配的总地址池。`hosts` 表示每个业务实际需要的主机数量，程序会从大到小分配最合适前缀，并列出剩余地址空间。

### flsm

用于 FLSM 等长子网划分。适合所有子网规模一致的场景，例如把一个网段平均切成若干个 VLAN，或每个分支都需要相同规模的地址池。

```text
parent           父网段，例如 10.0.0.0/24
--count COUNT    平均划分的子网数量
--hosts HOSTS    每个子网需要的主机数量，用于自动推导前缀
```

`--count` 用来指定要平均切成多少个子网。`--hosts` 用来指定每个子网至少容纳多少主机，程序会自动推导合适前缀。两者都填写时，会先按 `--hosts` 推导前缀，再只显示前 `--count` 个结果。

### overlap

用于检查多个网段是否互相包含、重叠或完全冲突。适合合并地址规划、排查路由冲突、审核 DHCP 地址池或确认多部门提交的网段是否撞车。

```text
networks         需要检查的网段列表，可填写多个
```

`networks` 接收多个 CIDR 网段。程序会两两比较，并给出冲突类型和冲突地址范围。

### summarize

用于路由汇总。适合整理静态路由、优化路由表、准备汇总路由公告，或检查多个连续网段能否聚合成更少的 CIDR。

```text
networks         需要汇总的网段列表，可填写多个
--force          按首尾地址强制汇总，并提示额外包含的地址范围
```

默认会生成精确覆盖输入网段的最小 CIDR 列表。使用 `--force` 时，会按输入网段的首尾地址生成一个覆盖范围更大的汇总网段，并提示该汇总会额外包含哪些地址空间。

### wildcard

用于 ACL wildcard 计算。适合编写 Cisco、Huawei 等网络设备 ACL 时，将单主机、网段或地址范围转换成 wildcard 表达。

```text
--host IP                单主机 IPv4 地址
--network NETWORK        IPv4 网段，例如 192.168.1.0/24
--range START END        IPv4 地址范围，会自动拆分为最小 CIDR 片段
```

`--host` 用于单个地址，wildcard 固定为 `0.0.0.0`。`--network` 用于普通网段。`--range` 用于起止地址范围，程序会自动拆成若干个可表达的 CIDR 片段并给出对应 wildcard。

### dhcp

用于 DHCP 地址池规划。适合从一个子网中排除网关、服务器、打印机、保留地址后，生成真正可分配给客户端的地址池。

```text
subnet                   DHCP 所属 IPv4 子网
--gateway IP             网关地址，必须在 subnet 内
--reserve VALUE          保留地址或地址范围，可重复使用，例如 192.168.1.10-192.168.1.20
```

`subnet` 是 DHCP 所在的 IPv4 网段。`--gateway` 会自动从可分配池中排除。`--reserve` 可重复填写，既可以是单个地址，也可以是 `起始-结束` 的地址范围；程序会检查保留范围是否合法。

### tree

用于地址空间树状展示。适合从父网段角度查看哪些子网已使用、哪些空间仍空闲，帮助理解整体地址规划。

```text
parent           父网段
used             已使用的子网列表，可为空或填写多个
```

`parent` 是需要观察的总地址空间。`used` 是已经分配出去的子网，程序会用树状结构展示父网段、已用空间和剩余空间。

## 用法示例

### IPv4 基础计算

```bash
python3 subnetting.py ipv4 192.168.1.10/24 -p
python3 subnetting.py ipv4 192.168.1.10/24 --mask 255.255.255.0 -o
```

输出网络地址、广播地址、可用地址范围、主机数量、掩码、反掩码和 wildcard。会正确处理 `/31` 点到点与 `/32` 主机路由。

### IPv6 基础计算

```bash
python3 subnetting.py ipv6 fd00::1/64 --child-prefix 80 -p
python3 subnetting.py ipv6 fe80::1/127 -p
```

输出网络前缀、地址范围、地址数量、地址类型，并识别单播、链路本地、ULA/private、组播等类型。会正确处理 `/127` 与 `/128`。

### VLSM 自动划分

```bash
python3 subnetting.py vlsm 192.168.10.0/24 office:100 guest:50 camera:20 p2p:2 -p
```

按主机需求从大到小自动分配最合适子网，并显示剩余地址空间。

### FLSM 等长划分

```bash
python3 subnetting.py flsm 10.0.0.0/24 --count 4 -p
python3 subnetting.py flsm 10.0.0.0/24 --hosts 50 -p
```

支持按指定数量平均划分，也支持按每个子网所需主机数自动推导前缀。

### 子网重叠检测

```bash
python3 subnetting.py overlap 10.0.0.0/24 10.0.0.128/25 10.0.1.0/24 -p
```

检查多个网段之间是否存在包含、重叠或完全冲突，并给出冲突地址范围。

### 路由汇总

```bash
python3 subnetting.py summarize 10.0.0.0/24 10.0.1.0/24 10.0.2.0/24 --force -p
```

生成最小 CIDR 汇总路由。使用 `--force` 时，会按首尾地址强制汇总，并提示可能额外包含的地址范围。

### ACL wildcard 计算

```bash
python3 subnetting.py wildcard --host 192.168.1.10 -p
python3 subnetting.py wildcard --network 192.168.1.0/24 -p
python3 subnetting.py wildcard --range 192.168.1.10 192.168.1.30 -p
```

输出 Cisco / Huawei ACL 可用的 wildcard 表达。地址范围会自动拆分为最小 CIDR 片段。

### DHCP 地址池规划

```bash
python3 subnetting.py dhcp 192.168.1.0/24 --gateway 192.168.1.1 --reserve 192.168.1.10-192.168.1.20 --reserve 192.168.1.100 -p
```

根据子网、网关和保留地址生成可分配地址池，并检查网关和保留范围是否合法。

### Markdown / CSV 导出

```bash
python3 subnetting.py vlsm 192.168.10.0/24 office:100 guest:50 --format md -o plan.md
python3 subnetting.py flsm 10.0.0.0/24 --count 8 --format csv -o subnet.csv
python3 subnetting.py ipv4 192.168.1.10/24 -o
```

当 `-o` 后面只跟文件名时，文件会输出到桌面。例如 `-o plan.md` 会写入 `~/Desktop/plan.md`。
未指定 `--format` 时，`.txt` 默认写入 Markdown，`.csv` 默认写入 CSV；指定 `--format` 时会使用指定格式。

### 地址空间树状可视化

```bash
python3 subnetting.py tree 192.168.10.0/24 192.168.10.0/26 192.168.10.64/27 -p
```

以树状结构展示父网段、已用子网和剩余空间。

## 注意

- 本工具面向合法的网络规划、教学演示、配置草稿生成和文档整理。
- IPv4 主机数量按常规可用地址计算，特殊处理 `/31` 与 `/32`。
- IPv6 地址范围按网络内地址空间展示，特殊处理 `/127` 与 `/128`。
