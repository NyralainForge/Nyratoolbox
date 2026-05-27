# Merged Generator CLI Print

一个非交互式命令行测试数据生成工具，用于生成格式合法、日期合法、校验码正确的 18 位身份证号样式字符串。

> 本项目仅用于软件测试、数据格式验证、教学演示等合法用途。  
> 生成结果为随机合成数据，不保证生成证唯一性，不代表真实身份信息，也不保证不会与真实号码发生偶然重合。
> 本工具只保证格式、日期和校验码合法，不保证 six_code 为真实行政区划码

参数说明：
   six_code       不携带 -dict 时使用，指定 6 位第一部分，执行生成单条功能
   -dict DICT     执行批量随机功能，并指定 6 位字典文件路径
   -sd            指定开始日期，格式 YYYYMMDD
   -ed            指定结束日期，格式 YYYYMMDD
   -norm          激活正态分布日期随机；不指定时使用均匀随机日期
   -s             指定按性别限制奇偶性：M=奇数，F=偶数；不指定则不限制
   -sn            指定 3 位顺序码起始值，范围 1-999；需要与 -snd 同时使用
   -snd           指定 3 位顺序码结束值，范围 1-999；需要与 -sn 同时使用
   -o             指定输出路径和文件名
   -n             指定输出条目数量；不指定默认 1 

- 生成单条模式下，如果没有指定 -o 且实际只生成 1 条，则直接打印到屏幕。
- 其他情况写入文件；未指定 -o 时默认写入 ~/Desktop/out.txt。
- 正常情况下，-ed 默认为系统当前日期，-sd 默认为系统当前日期往前 30000 天。
- 如果获取到的系统年份小于 2025，且用户没有显式指定 -sd / -ed，则继续使用旧默认范围：19610101 到 20261231。

## Features

- 支持生成单条结果
- 支持从 6 位地区码字典中批量随机生成
- 支持指定出生日期范围
- 默认使用均匀随机日期
- 可通过 `-norm` 启用正态分布日期随机
- 支持按性别限制顺序码奇偶性
- 自动计算第 18 位校验码
- 支持输出到文件
- 单条模式下可直接打印到终端

## 字典文件格式

`-dict` 参数用于指定 6 位地区码字典文件。字典文件中的每个有效值必须是 **6 位纯数字**。

支持常见文本格式：

- `.txt` / `.list` / `.dict`：支持一行一个值，也支持空格、逗号、分号、Tab 分隔
- `.csv`：支持常见 CSV 格式，可包含表头
- `.tsv` / `.tab`：支持 Tab 分隔格式
- 兼容 UTF-8 BOM / UTF-8-SIG 文件头
- 空行会被忽略
- 以 `#` 或 `//` 开头的行会被视为注释并忽略

示例：

```text
# dict6.txt
110101
310101
440305

## Requirements

- Python 3.10+

本项目仅使用 Python 标准库，无需额外安装依赖。

## Usage

生成单条模式：
  python3 merged_generator_cli_print.py 110101 -sd 19990522 -ed 19990522
  python3 merged_generator_cli_print.py 110101 -sd 19990522 -ed 19990522 -s F -o one.txt
  python3 merged_generator_cli_print.py 110101 -sd 19600101 -ed 20001231 -norm
  python3 merged_generator_cli_print.py 110101 -sd 19990522 -ed 19990522 -sn 200 -snd 999

批量随机模式：
  python3 merged_generator_cli_print.py -dict dict6.txt -sd 19600101 -ed 20001231 -s M -n 1000 -o out.txt
  python3 merged_generator_cli_print.py -dict dict6.txt -sd 19600101 -ed 20001231 -norm -n 1000 -o out.txt
  python3 merged_generator_cli_print.py -dict dict6.txt -sd 19600101 -ed 20001231 -sn 200 -snd 999 -n 1000 -o out.txt



# Merged Generator CLI Print

一个非交互式命令行测试数据生成工具，用于生成格式合法、日期合法、校验码正确的 18 位身份证号样式字符串。

> 本项目仅用于软件测试、数据格式验证、教学演示等合法用途。  
> 生成结果为随机合成数据，不保证生成结果唯一性，不代表真实身份信息，也不保证不会与真实号码发生偶然重合。  
> 本工具只保证格式、日期和校验码合法，不保证 `six_code` 为真实行政区划码。

## Features

- 支持生成单条结果
- 支持从 6 位地区码字典中批量随机生成
- 支持指定出生日期范围
- 默认使用均匀随机日期
- 可通过 `-norm` 启用正态分布日期随机
- 支持按性别限制顺序码奇偶性
- 自动计算第 18 位校验码
- 支持输出到文件
- 单条模式下可直接打印到终端

## Parameters

```text
six_code       不携带 -dict 时使用，指定 6 位第一部分，执行生成单条功能
-dict DICT     执行批量随机功能，并指定 6 位字典文件路径
-sd            指定开始日期，格式 YYYYMMDD
-ed            指定结束日期，格式 YYYYMMDD
-norm          激活正态分布日期随机；不指定时使用均匀随机日期
-s             指定按性别限制奇偶性：M=奇数，F=偶数；不指定则不限制
-sn            指定 3 位顺序码起始值，范围 1-999；需要与 -snd 同时使用
-snd           指定 3 位顺序码结束值，范围 1-999；需要与 -sn 同时使用
-o             指定输出路径和文件名
-n             指定输出条目数量；不指定默认 1
```

## Default Behavior

- 生成单条模式下，如果没有指定 `-o` 且实际只生成 1 条，则直接打印到屏幕。
- 其他情况写入文件；未指定 `-o` 时默认写入 `~/Desktop/out.txt`。
- 正常情况下，`-ed` 默认为系统当前日期，`-sd` 默认为系统当前日期往前 30000 天。
- 如果获取到的系统年份小于 2025，且用户没有显式指定 `-sd` / `-ed`，则继续使用旧默认范围：`19610101` 到 `20261231`。
- 未指定 `-sn` / `-snd` 时，默认只在 `001-100` 内按加权概率生成：`001-050` 占 65%，`051-100` 占 35%。
- 本工具不保证输出结果唯一；当日期范围、地区码或顺序码范围较小时，可能出现重复。

## Dictionary File Format

`-dict` 参数用于指定 6 位地区码字典文件。字典文件中的每个有效值必须是 **6 位纯数字**。

支持常见文本格式：

- `.txt` / `.list` / `.dict`：支持一行一个值，也支持空格、逗号、分号、Tab 分隔
- `.csv`：支持常见 CSV 格式，可包含表头
- `.tsv` / `.tab`：支持 Tab 分隔格式
- 兼容 UTF-8 BOM / UTF-8-SIG 文件头
- 空行会被忽略
- 以 `#` 或 `//` 开头的行会被视为注释并忽略

如果文件中出现非表头、非注释、非空白且不是 6 位数字的字段，程序会报错。

示例：

```text
# dict6.txt
110101
310101
440305
```

```csv
code
110101
310101
440305
```

> 注意：字典值只校验是否为 6 位数字，不校验是否为真实行政区划码。

## Requirements

- Python 3.10+

本项目仅使用 Python 标准库，无需额外安装依赖。

## Usage

### Single Mode

```bash
python3 merged_generator_cli_print.py 110101 -sd 19990522 -ed 19990522
python3 merged_generator_cli_print.py 110101 -sd 19990522 -ed 19990522 -s F -o one.txt
python3 merged_generator_cli_print.py 110101 -sd 19600101 -ed 20001231 -norm
python3 merged_generator_cli_print.py 110101 -sd 19990522 -ed 19990522 -sn 200 -snd 999
```

### Batch Mode

```bash
python3 merged_generator_cli_print.py -dict dict6.txt -sd 19600101 -ed 20001231 -s M -n 1000 -o out.txt
python3 merged_generator_cli_print.py -dict dict6.txt -sd 19600101 -ed 20001231 -norm -n 1000 -o out.txt
python3 merged_generator_cli_print.py -dict dict6.txt -sd 19600101 -ed 20001231 -sn 200 -snd 999 -n 1000 -o out.txt
```