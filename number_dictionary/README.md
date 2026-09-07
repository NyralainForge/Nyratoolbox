# Number Generator CLI

一个非交互式命令行测试数据生成工具，用于生成指定长度的随机数字、基于字典号段补全的手机号，以及数字邮箱。

> 本项目仅用于软件测试、数据格式验证、教学演示等合法用途。  
> 生成结果为随机合成数据，不代表真实账号、真实邮箱或真实用户信息，也不保证不会与真实号码或邮箱发生偶然重合。  
> 请勿将本工具用于撞库、批量注册、垃圾邮件、钓鱼、骚扰、绕过风控等非法或不当用途。

## Features

- 支持随机生成指定长度的数字字符串
- 支持通过批量生成多条结果
- 支持从字典文件中读取基础数据并混合随机输出
- 支持输出结果自动去重
- 多条输出时默认写入文件
- 支持常见字典文件格式和 UTF-8 BOM 文件头

## Parameters

```text
length         普通模式必填的正整数，指定随机数字长度；不与 -dict / -q / -qn 同用
-dict DICT     指定字典文件路径，从字典中读取候选值并参与随机输出
-m [SUFFIX]    邮箱后缀开关；不输入则不拼接，单独输入则随机默认后缀，携带参数则使用指定后缀
-q [LENGTH]    启用 QQ 邮箱模式，可指定数字长度，并拼接 @qq.com
-qn            启用 QQ 号码权重模式，按指定概率生成 7-11 位数字并拼接 @qq.com
-o OUTPUT      指定输出路径和文件名
-n COUNT       指定输出条目数量；不指定默认 1
```

## Default Behavior

- 普通模式的位置参数表示长度，例如 `10` 生成 10 位随机数字，首位不为 0；不保证符合手机号规则。
- 未指定 `-m` 时，普通模式只生成数字，不拼接邮箱后缀。
- 单独输入 `-m` 且不携带参数时，普通模式会在以下后缀中随机选择一个，本次生成的所有普通结果使用同一个后缀：

```text
@139.com
@163.com
@162.com
```

- 输入 `-m SUFFIX` 时，所有普通随机数字结果都会拼接指定后缀。
- `-q` 单独使用且不带 `-dict` 时，随机生成 9-11 位数字并拼接 `@qq.com`。
- `-q length` 且不带 `-dict` 时，随机生成指定长度的数字并拼接 `@qq.com`。
- `-qn` 且不带 `-dict` 时，随机生成 7-11 位数字并拼接 `@qq.com`，长度权重如下：

```text
10 位：50%
9 位：35%
11 位：10%
7-8 位：5%
```

- 输入 `-q` 或 `-qn` 且同时指定 `-dict` 时，会将字典结果与随机生成结果混合后随机输出。
- 所有输出结果都会去重并按字符串排序；请求数量超过可生成的不重复结果数时会报错。
- 当 `-n` 指定多条输出时，程序不直接把结果打印到屏幕，而是写入文件。
- 未指定 `-o` 时，默认输出到：

```text
~/Desktop/out.txt
```

## Dictionary File Format

`-dict` 参数用于指定字典文件。字典文件中的纯数字值会作为候选数据参与输出，非数字表头和说明字段会被忽略。

- 7 位数字按号段处理，随机补 4 位数字，生成 11 位号码；项目自带的 `phonetmp.csv` 使用此格式。
- 其他长度的数字直接作为完整候选值输出，保留前导零，不再补数字。
- 重复候选值会被去重；只有 3 个完整号码的字典，不加 QQ 模式时最多生成 3 条结果。

支持常见文本格式：

- `.txt` / `.list` / `.dict`：支持一行一个值，也支持空格、逗号、分号、Tab 分隔
- `.csv`：支持常见 CSV 格式，可包含表头
- `.tsv` / `.tab`：支持 Tab 分隔格式
- 兼容 UTF-8 BOM / UTF-8-SIG 文件头
- 空行会被忽略
- 以 `#` 或 `//` 开头的行会被视为注释并忽略

示例：

```text
# phonetmp.txt
13800138000
13900139000
15600156000
```

```csv
number
13800138000
13900139000
15600156000
```

> 注意：字典值只作为候选字符串读取，不保证其真实性、可用性或归属关系。

## Requirements

- Python 3.10+

本项目仅使用 Python 标准库，无需额外安装依赖。

## Usage

以下命令请在 `number_dictionary` 目录中运行。输出为实际运行示例，每次随机结果会不同。`~/Desktop/out.txt` 在终端中会显示为当前用户的绝对路径。文件内容仅展示前 3 行（不足 3 行则全部展示）。

### Normal Mode

生成单条随机数字结果：

```bash
python3 number.py 10
```

终端输出示例：

```text
4352375402
```

生成 10 条随机数字结果，不拼接邮箱后缀：

```bash
python3 number.py 10 -n 10
```

终端输出示例：

```text
已生成 10 条结果，已输出到文件: /Users/admin/Desktop/out.txt
```

文件内容节选：

```text
2128170403
2689570135
4280672506
```

生成 10 条随机结果，并随机拼接默认邮箱后缀：

```bash
python3 number.py 10 -n 10 -m
```

终端输出示例：

```text
已生成 10 条结果，已输出到文件: /Users/admin/Desktop/out.txt
```

文件内容节选：

```text
1433517875@139.com
3268581749@139.com
3413563787@139.com
```

生成 10 条随机结果，并指定邮箱后缀：

```bash
python3 number.py 10 -n 10 -m @163.com
```

终端输出示例：

```text
已生成 10 条结果，已输出到文件: /Users/admin/Desktop/out.txt
```

文件内容节选：

```text
3209518372@163.com
3948166198@163.com
6071286574@163.com
```

生成 10 条随机结果，并输出到指定文件：

```bash
python3 number.py 10 -n 10 -m @163.com -o out.txt
```

终端输出示例：

```text
已生成 10 条结果，已输出到文件: out.txt
```

文件内容节选：

```text
1631099971@163.com
2238714500@163.com
4177890915@163.com
```

### Dictionary Mode

从字典文件中读取候选值，并生成 10 条结果：

```bash
python3 number.py -dict phonetmp.csv -n 10
```

终端输出示例：

```text
已生成 10 条结果，已输出到文件: /Users/admin/Desktop/out.txt
```

文件内容节选：

```text
13500673109
14595198883
14765856099
```

从字典文件中读取候选值，并随机拼接默认邮箱后缀：

```bash
python3 number.py -dict phonetmp.csv -n 10 -m
```

终端输出示例：

```text
已生成 10 条结果，已输出到文件: /Users/admin/Desktop/out.txt
```

文件内容节选：

```text
13322235971@163.com
17667704664@163.com
17805500024@163.com
```

从字典文件中读取候选值，并统一拼接指定后缀：

```bash
python3 number.py -dict phonetmp.csv -n 10 -m @163.com
```

终端输出示例：

```text
已生成 10 条结果，已输出到文件: /Users/admin/Desktop/out.txt
```

文件内容节选：

```text
13209831021@163.com
13538325458@163.com
13598002517@163.com
```

指定完整输出路径：

```bash
python3 number.py -dict phonetmp.csv -n 10 -m @163.com -o ~/Desktop/out.txt
```

终端输出示例：

```text
已生成 10 条结果，已输出到文件: /Users/admin/Desktop/out.txt
```

文件内容节选：

```text
13834551778@163.com
14915949665@163.com
14925644072@163.com
```

### QQ Mode

随机生成 9-11 位 QQ 邮箱：

```bash
python3 number.py -q
```

终端输出示例：

```text
34483025858@qq.com
```

随机生成指定长度的 QQ 邮箱：

```bash
python3 number.py -q 10
```

终端输出示例：

```text
5290965525@qq.com
```

生成 100 条 QQ 邮箱：

```bash
python3 number.py -q -n 100
```

终端输出示例：

```text
已生成 100 条结果，已输出到文件: /Users/admin/Desktop/out.txt
```

文件内容节选：

```text
102812129@qq.com
103421754@qq.com
111890411@qq.com
```

启用 QQ 号码权重模式：

```bash
python3 number.py -qn -n 100
```

终端输出示例：

```text
已生成 100 条结果，已输出到文件: /Users/admin/Desktop/out.txt
```

文件内容节选：

```text
10014997064@qq.com
118275975@qq.com
123454932@qq.com
```

### Mixed Dictionary + QQ Mode

将字典结果与 QQ 随机结果混合输出：

```bash
python3 number.py -q -dict phonetmp.csv -n 100
```

终端输出示例：

```text
已生成 100 条结果，已输出到文件: /Users/admin/Desktop/out.txt
```

文件内容节选：

```text
116583579@qq.com
1244688823@qq.com
13077601732
```

使用 QQ 权重模式，并与字典结果混合输出：

```bash
python3 number.py -qn -dict phonetmp.csv -n 100
```

终端输出示例：

```text
已生成 100 条结果，已输出到文件: /Users/admin/Desktop/out.txt
```

文件内容节选：

```text
1029632801@qq.com
10302185363@qq.com
112300494@qq.com
```

## Output

单条输出时，结果可能直接显示在终端中：

```text
1234567890
```

多条输出时，程序会写入文件，并显示输出路径：

```text
已生成 10 条结果，已输出到文件: /Users/admin/Desktop/out.txt
```

## Notes

- 当候选空间过小时，去重可能导致实际可生成数量受限。
- 如果需要生成大量结果，建议提供足够大的数字长度、字典规模或候选范围。
- `-m` 可单独使用；如需指定后缀，使用包含 `@` 的完整后缀，例如 `@163.com`。
- `-q` / `-qn` 模式默认使用 `@qq.com`，通常不需要再指定 `-m`。
