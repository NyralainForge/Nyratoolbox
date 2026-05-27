# ShortID Dictionary

生成偶数长度的十六进制 ShortID 穷举列表。

> 本工具仅用于合法的软件测试、数据格式验证、教学演示和个人自动化用途。

## 参数

```text
-l   十六进制字符长度，必须是偶数，例如 2、4、6
-sl  数列开始位置，默认 0
-el  数列结束位置，默认是当前长度的最大位置
-n   生成的列表长度
-r   随机生成，并对本次输出去重复
-o   指定输出文件路径；默认保存到 ~/Desktop/out.txt
```

规则：

- 数列位置从 `0` 开始。
- `-l 4` 时，第 `0` 项是 `0000`，第 `65535` 项是 `ffff`。
- 若 `-l` 大于 `4`，或输出范围大于等于 `16^6`，必须指定 `-n`。
- 输出条目仅为一条且未指定 `-o` 时，不生成文件，只打印到屏幕。
- 写文件时逐条生成、逐条写入，避免一次性保存大量数据到内存。

## 用法

```bash
python3 shortid.py -l 4
python3 shortid.py -l 6 -n 1000
python3 shortid.py -l 6 -sl 100 -el 9999 -n 50
python3 shortid.py -l 8 -n 10000 -r -o ~/Desktop/shortid.txt
python3 shortid.py -l 2 -sl 15 -n 1
```

