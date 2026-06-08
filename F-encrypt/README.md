# F-encrypt

一个命令行加密 / 解密工具，使用 AES-GCM 加密数据，并将密文编码为以 `如是我闻：` 开头的伪经文文本。

> 本工具仅用于合法的个人数据保护、软件测试、教学演示和临时自动化用途。请妥善保存密码；密码丢失后无法恢复明文。

## Features

- 支持加密普通命令行文本
- 支持加密 / 解密常见文本类文件
- 文件模式使用二进制读写，保留原始 bytes
- 可保留 BOM、CRLF/LF 换行、NUL、非 UTF-8 字节等内容
- 加密结果输出为可复制保存的密文文本
- 解密文件时按原始 bytes 写回
- 支持 `-ecc` 生成带自动纠错能力的密文
- 使用扩展音译咒文字表，降低密文正文的重复感
- 支持 `-o` 指定输出路径和文件名

## Requirements

- Python 3.10+
- `cryptography`

安装依赖：

```bash
python3 -m pip install cryptography
```

## 参数

```text
-encrypt        加密模式；默认也是加密模式
-decrypt        解密模式
-ecc            加密时启用 ECC 自动纠错编码
-o OUTPUT       指定输出路径和文件名
```

`-encrypt` 和 `-decrypt` 不能同时使用。

`-ecc` 只需要在加密时指定；解密时程序会自动识别 ECC 密文并尝试纠错。

## 文件模式

当 `-encrypt` 或 `-decrypt` 后面挂载一个已存在的受支持文件时，程序会进入文件模式。

支持的文件后缀：

```text
.txt .md .markdown .text .log .csv .json .jsonl .yaml .yml .xml .html .htm .ini .cfg .conf .rst
```

文件模式规则：

- 加密时使用 `read_bytes()` 读取原文件，再加密原始 bytes。
- 解密时恢复原始 bytes，并使用 `write_bytes()` 写回。
- 文件模式强制输出到文件。
- 指定 `-o` 时，输出到 `-o` 指定的路径和文件名。
- 未指定 `-o` 时，默认输出到 `~/Desktop/out.txt`。
- 如果输入路径看起来像文件但不存在，程序会报错，不会误当成普通文本加密。

## 用法

加密普通文本，结果打印到屏幕：

```bash
python3 F-encrypt.py -encrypt "hello world"
```

加密文件，并指定输出密文文件：

```bash
python3 F-encrypt.py -encrypt config.conf -o secret.txt
python3 F-encrypt.py -encrypt note.md -o encrypted.txt
```

加密文件，不指定输出路径时写入桌面：

```bash
python3 F-encrypt.py -encrypt config.conf
```

输出文件：

```text
~/Desktop/out.txt
```

解密密文文件，并恢复为原始文件 bytes：

```bash
python3 F-encrypt.py -decrypt secret.txt -o restored.conf
```

启用 ECC 自动纠错加密：

```bash
python3 F-encrypt.py -encrypt -ecc config.conf -o secret.txt
python3 F-encrypt.py -encrypt -ecc "hello world"
```

解密 ECC 密文时不需要再指定 `-ecc`：

```bash
python3 F-encrypt.py -decrypt secret.txt -o restored.conf
```

通过管道加密 bytes：

```bash
cat config.conf | python3 F-encrypt.py -encrypt -o secret.txt
```

通过管道解密密文：

```bash
cat secret.txt | python3 F-encrypt.py -decrypt -o restored.conf
```

## 输出行为

- 普通文本加密：未指定 `-o` 时打印密文到屏幕。
- 普通文本解密：未指定 `-o` 时把明文 bytes 写到 stdout。
- 文件加密：必须输出到文件，默认 `~/Desktop/out.txt`。
- 文件解密：必须输出到文件，默认 `~/Desktop/out.txt`。

## ECC 自动纠错

`-ecc` 会在伪经文密文的字符层加入分块校验符号。正文字符不会重复铺开，程序会按块混入少量纠错符号，也不会在开头或结尾写入明显的 ECC 标记。解密时程序会先尝试普通解密，失败后自动按 ECC 结构修复字符层错误，再进入 AES-GCM 解密。

可纠正：

- 每个 ECC 块中最多 1 个字符被替换或污染
- 每个 ECC 块中最多 1 个非法字符
- 少量分散在不同块中的单字符错误

不能纠正：

- 字符插入或删除
- 同一个 ECC 块中有 2 个或更多字符损坏
- 大面积截断或顺序错乱

启用 ECC 后密文会略微变长。当前实现每 64 个正文字符追加 2 个纠错字符。

当前密文字表包含常见音译咒文用字，例如六字大明咒、般若心经咒、准提咒、大悲咒、楞严咒心等片段中的常见汉字 / 音译字，并会过滤空白字符。因为字表已经扩展，旧版本生成的密文不再兼容。

## 注意

- 密码通过终端隐藏输入，不会显示在屏幕上。
- 解密失败通常表示密码错误，或密文内容被修改过。
- 加密输出是文本密文；解密输出是原始 bytes。
- 未启用 `-ecc` 的普通密文只能检测损坏，不能自动纠错。
- 如果要完整保留文件内容，请优先使用文件模式或管道模式，避免把内容作为命令行普通文本传入。
