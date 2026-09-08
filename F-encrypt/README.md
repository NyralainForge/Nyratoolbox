# F-encrypt

一个命令行加密 / 解密工具，使用 AES-GCM 加密数据，默认输出无填充的 URL-safe Base64 密文。加密时使用 `-sutra` 可输出以 `如是我闻：` 开头的伪经文。解密自动识别两种格式。

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
-sutra          加密时输出伪经文；不指定则输出 Base64
-recursive      允许递归加密或解密一个目录（默认禁止目录输入）
-delete-source  加密并验证密文后删除对应原文件（默认保留）
-o OUTPUT       指定输出路径和文件名
--              后续参数全部按直接文本处理（包括以 - 开头的密文）
```

`-encrypt` 和 `-decrypt` 不能同时使用。

`-ecc` 只需要在加密时指定；解密时程序会自动识别 ECC 密文并尝试纠错。

`-sutra` 和 `-ecc` 相互独立，可以单独使用或组合使用。解密无需指定这两个参数。

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

输出伪经文，或同时启用纠错：

```bash
python3 F-encrypt.py -encrypt -sutra "hello world"
python3 F-encrypt.py -encrypt -sutra -ecc config.conf -o secret.txt
python3 F-encrypt.py -decrypt secret.txt -o restored.conf
```

直接传入密文时，建议使用 `--`，避免 Base64 密文开头的 `-` 被当作选项，或长密文被当作文件路径：

```bash
python3 F-encrypt.py -decrypt -- "这里替换为完整密文"
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

### 递归处理目录

`-recursive` 支持目录加密和解密。加密时处理所有普通文件，包括无后缀和二进制文件；解密时仅处理以 `.encrypted.txt` 结尾的文件。单文件模式的后缀限制仍保持不变。符号链接及其他非普通文件跳过，不跟随符号链接目录。整个批次只输入一次密码。

未指定 `-recursive` 时，任何输入参数指向已存在的目录都会在输入密码前报错，包括目录与其他文本混用、目录符号链接，以及 `--` 后的目录路径。`--` 不能绕过此检查。`-recursive` 必须显式提供且目标为一个真实目录；参数位于目录路径之前或之后均可。

```bash
python3 F-encrypt.py -encrypt ./configs -recursive -o ./encrypted
python3 F-encrypt.py -encrypt ./configs -recursive -sutra -ecc -o ./encrypted
```

目录模式下 `-o` 表示输出目录；仅使用 `-recursive` 时，省略 `-o` 默认输出到 `~/Desktop/out`。同时使用 `-recursive -delete-source` 且省略 `-o` 时，密文输出在各原文件旁边，验证成功后删除原文件。

密文文件名在原文件名后追加 `.encrypted.txt`。指定输出目录时保留相对目录结构，例如 `configs/sub/app.yaml` 输出为 `encrypted/sub/app.yaml.encrypted.txt`；原目录输出时则生成 `configs/sub/app.yaml.encrypted.txt`。原目录模式跳过已有的 `.encrypted.txt` 文件，避免再次加密。除这一默认原目录模式外，输出目录不得等于输入目录或位于其内部。已有同名输出文件会报错，目录内为空时不生成密文。

递归解密自动识别 Base64、伪经文和 ECC，去掉文件名最后的 `.encrypted.txt` 后缀，并按原始 bytes 恢复内容及相对目录结构。未指定 `-o` 时输出到 `~/Desktop/out`，同名输出文件会报错。密文保留，`-delete-source` 仍仅用于加密。遇到错误密码或损坏密文时停止，当前文件不会输出未经认证的明文，已完成的文件保留。

```bash
python3 F-encrypt.py -decrypt ./encrypted -recursive -o ./restored
```

也可以按单文件解密：

```bash
python3 F-encrypt.py -decrypt ./encrypted/sub/app.yaml.encrypted.txt -o ./restored/app.yaml
```

### 加密后删除原文件

`-delete-source` 可用于单文件加密或与 `-recursive` 组合，不能用于直接文本、stdin 或解密。

```bash
python3 F-encrypt.py -encrypt config.conf -delete-source -o secret.txt
python3 F-encrypt.py -encrypt ./configs -recursive -delete-source -o ./encrypted
python3 F-encrypt.py -encrypt ./configs -recursive -delete-source
```

启用删除时，密文须成功写入、同步、关闭，并回读解密为完全一致的原始 bytes，随后确认原文件未在处理期间变化，才删除该原文件。写入或验证失败时保留原文件并报错。递归模式及启用删除的单文件模式均拒绝覆盖已有输出，也拒绝原文件与输出文件为同一路径。

删除仅指普通文件删除，不是安全擦除；目录本身保留。批处理遇错立即停止，此前已成功写入或删除的文件不会回滚；失败产生的部分输出文件可能保留，重试前需检查处理。

### 单文件和文本

- 普通文本加密：未指定 `-o` 时打印密文到屏幕。
- 普通文本解密：未指定 `-o` 时把明文 bytes 写到 stdout。
- 文件加密：必须输出到文件，默认 `~/Desktop/out.txt`。
- 文件解密：必须输出到文件，默认 `~/Desktop/out.txt`。

## ECC 自动纠错

`-ecc` 在所选输出格式的字符层加入分块校验符号。Base64 模式的校验字符还可能包含 `.`、`~`、`!`，因此启用 ECC 后不是标准 Base64，需由本程序解码。伪经文模式使用咒文字表。两种模式均无显式 ECC 标记；解密先尝试无 ECC 的解码，失败后尝试纠错，并且只有 AES-GCM 认证通过才返回明文。

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
