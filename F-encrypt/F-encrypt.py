# AES-GCM 加密工具，默认输出 Base64，使用 -sutra 输出伪经文。
import base64
import os
import sys
from getpass import getpass
from pathlib import Path
from typing import NamedTuple

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt


PREFIX = "如是我闻："
SENTINEL = b"\x01"
DEFAULT_FILE_OUTPUT = Path.home() / "Desktop" / "out.txt"
SUPPORTED_TEXT_SUFFIXES = {
    ".txt",
    ".md",
    ".markdown",
    ".text",
    ".log",
    ".csv",
    ".json",
    ".jsonl",
    ".yaml",
    ".yml",
    ".xml",
    ".html",
    ".htm",
    ".ini",
    ".cfg",
    ".conf",
    ".rst",
}

ALPHABET = (
    "唵修利修利摩诃修利修修利萨婆诃"
    "唵娑嚩婆嚩秫驮娑嚩达摩娑嚩婆嚩秫度憾 "
    "唵修多唎修多唎修摩唎修摩唎娑婆诃"
    "唵嚩日啰怛诃贺斛"
    "南无三满哆母驮喃唵度噜度噜地尾萨婆诃"
    "唵誐誐曩，三婆嚩伐日啰斛"
    "嗡嘛呢叭咪吽"
    "揭谛揭谛波罗揭谛波罗僧揭谛菩提萨婆诃"
    "南无喝啰怛那哆啰夜耶阿唎耶婆卢羯帝烁钵啰耶"
    "菩提萨埵婆耶摩诃萨埵婆耶摩诃迦卢尼迦耶"
    "萨皤啰罚曳数怛那怛写悉吉栗埵伊蒙阿唎耶"
    "婆卢吉帝室佛啰楞驮婆那啰谨墀醯利摩诃皤哆沙咩"
    "萨婆阿他豆输朋阿逝孕萨婆萨哆那摩婆萨哆那摩婆伽"
    "摩罚特豆怛侄他阿婆卢醯卢迦帝迦罗帝夷醯唎"
    "摩诃菩提萨埵萨婆萨婆摩罗摩罗摩醯摩醯唎驮孕"
    "俱卢俱卢羯蒙度卢度卢罚阇耶帝摩诃罚阇耶帝"
    "陀罗陀罗地唎尼室佛啰耶遮罗遮罗摩摩罚摩啰"
    "穆帝隶伊醯伊醯室那室那阿啰嘇佛啰舍利"
    "罚沙罚嘇佛罗舍耶呼卢呼卢摩啰呼卢呼卢醯利"
    "娑啰娑啰悉唎悉唎苏嚧苏嚧菩提夜菩提夜菩驮夜菩驮夜"
    "弥帝唎夜那啰谨墀地利瑟尼那波夜摩那娑婆诃"
    "南无飒哆喃三藐三勃陀俱胝南怛姪他折隶主隶准提"
    "怛姪他阿那隶毗舍提鞞啰跋阇啰陀唎槃陀你"
    "跋阇啰谤尼泮虎都嚧瓮泮娑婆诃"
    "娜么悉底野陀尾迦南萨嚩怛他誐跢南暗尾囉爾"
    "些囉帝怛邏異尾馱麼儞三畔若儞悉馱仡㘑怛㘕沙嚩訶"
    "般若波罗蜜多故说咒曰羯谛羯谛波罗羯谛波罗僧羯谛"
)

ALPHABET = "".join(dict.fromkeys(ch for ch in ALPHABET if not ch.isspace()))
ECC_EXTRA_SYMBOLS = "吒咤呬抳拏"
ECC_ALPHABET = ALPHABET + "".join(
    ch for ch in ECC_EXTRA_SYMBOLS if ch not in ALPHABET
)
ECC_FIELD_SIZE = len(ECC_ALPHABET)
ECC_DATA_SYMBOLS = 64
BASE64_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_"
BASE64_ECC_ALPHABET = BASE64_ALPHABET + ".~!"


class ParsedArgs(NamedTuple):
    mode: str
    output_path: str | None
    text: str | None
    input_path: Path | None
    ecc: bool
    sutra: bool
    recursive: bool
    delete_source: bool


def derive_key(password: str, salt: bytes) -> bytes:
    kdf = Scrypt(
        salt=salt,
        length=32,
        n=2**14,
        r=8,
        p=1,
    )
    return kdf.derive(password.encode("utf-8"))


def bytes_to_sutra(data: bytes) -> str:
    # 加一个固定哨兵字节，防止 int <-> bytes 转换时丢失开头的 0x00
    wrapped_data = SENTINEL + data
    n = int.from_bytes(wrapped_data, "big")
    base = len(ALPHABET)

    chars = []
    while n > 0:
        n, r = divmod(n, base)
        chars.append(ALPHABET[r])

    body = "".join(reversed(chars))
    return f"{PREFIX}{body}"


def bytes_to_ecc_sutra(data: bytes) -> str:
    body = bytes_to_sutra(data)[len(PREFIX):]
    protected_body = encode_ecc_body(body)
    return f"{PREFIX}{protected_body}"


def sutra_to_bytes(text: str) -> bytes:
    if not text.startswith(PREFIX):
        raise ValueError("不是有效的密文格式")

    body = text[len(PREFIX):]
    if not body:
        raise ValueError("密文内容为空")

    table = {ch: i for i, ch in enumerate(ALPHABET)}
    base = len(ALPHABET)

    n = 0
    for ch in body:
        if ch not in table:
            raise ValueError(f"发现非法字符：{ch}")
        n = n * base + table[ch]

    byte_length = (n.bit_length() + 7) // 8
    wrapped_data = n.to_bytes(byte_length, "big")

    if not wrapped_data.startswith(SENTINEL):
        raise ValueError("格式损坏")

    return wrapped_data[len(SENTINEL):]


def ecc_sutra_to_bytes(text: str) -> bytes:
    if not text.startswith(PREFIX):
        raise ValueError("不是有效的密文格式")

    body = text[len(PREFIX):]
    if not body:
        raise ValueError("ECC 密文内容为空")

    repaired_body = decode_ecc_body(body)
    return sutra_to_bytes(f"{PREFIX}{repaired_body}")


def encode_ecc_body(body: str, alphabet: str = ALPHABET,
                    ecc_alphabet: str = ECC_ALPHABET) -> str:
    table = {ch: i for i, ch in enumerate(alphabet)}
    symbols = [table[ch] for ch in body]
    encoded_blocks = []

    for i in range(0, len(symbols), ECC_DATA_SYMBOLS):
        encoded_blocks.append(encode_ecc_block(symbols[i:i + ECC_DATA_SYMBOLS], ecc_alphabet))

    return "".join(encoded_blocks)


def encode_ecc_block(data_symbols: list[int], ecc_alphabet: str = ECC_ALPHABET) -> str:
    field_size = len(ecc_alphabet)
    data_len = len(data_symbols)
    total = sum(data_symbols) % field_size
    weighted_total = sum(
        (i + 1) * value for i, value in enumerate(data_symbols)
    ) % field_size

    parity_2 = ((data_len + 1) * total - weighted_total) % field_size
    parity_1 = (-total - parity_2) % field_size
    codeword = data_symbols + [parity_1, parity_2]

    return "".join(ecc_alphabet[value] for value in codeword)


def decode_ecc_body(body: str, alphabet: str = ALPHABET,
                    ecc_alphabet: str = ECC_ALPHABET) -> str:
    if len(body) < 3:
        raise ValueError("ECC 密文长度损坏")

    decoded_chars = []
    i = 0
    while i < len(body):
        remaining = len(body) - i
        block_length = min(ECC_DATA_SYMBOLS + 2, remaining)
        if block_length < 3:
            raise ValueError("ECC 密文长度损坏")

        decoded_chars.append(decode_ecc_block(body[i:i + block_length], alphabet, ecc_alphabet))
        i += block_length

    return "".join(decoded_chars)


def decode_ecc_block(block: str, alphabet: str = ALPHABET,
                     ecc_alphabet: str = ECC_ALPHABET) -> str:
    values: list[int | None] = []
    erasure_index = None

    for i, ch in enumerate(block):
        index = ecc_alphabet.find(ch)
        if index == -1:
            if erasure_index is not None:
                raise ValueError("ECC 纠错失败：同一块中存在多个非法字符")
            erasure_index = i
            values.append(None)
        else:
            values.append(index)

    if erasure_index is not None:
        repair_erasure(values, erasure_index, len(ecc_alphabet))
    else:
        repair_substitution(values, len(ecc_alphabet))

    data_values = values[:-2]
    if any(value is None or value >= len(alphabet) for value in data_values):
        raise ValueError("ECC 纠错失败：数据符号损坏")

    return "".join(alphabet[value] for value in data_values)


def repair_erasure(values: list[int | None], erasure_index: int,
                   field_size: int = ECC_FIELD_SIZE) -> None:
    known_sum = sum(value for value in values if value is not None)
    repaired_value = (-known_sum) % field_size
    weighted_sum = sum(
        (i + 1) * value
        for i, value in enumerate(values)
        if value is not None
    )

    if ((erasure_index + 1) * repaired_value + weighted_sum) % field_size != 0:
        raise ValueError("ECC 纠错失败：非法字符无法恢复")

    values[erasure_index] = repaired_value


def repair_substitution(values: list[int | None], field_size: int = ECC_FIELD_SIZE) -> None:
    symbol_sum = sum(value for value in values if value is not None) % field_size
    weighted_sum = sum(
        (i + 1) * value
        for i, value in enumerate(values)
        if value is not None
    ) % field_size

    if symbol_sum == 0 and weighted_sum == 0:
        return
    if symbol_sum == 0:
        raise ValueError("ECC 纠错失败：错误数量超过纠错能力")

    error_position = (
        weighted_sum * pow(symbol_sum, -1, field_size)
    ) % field_size
    if error_position < 1 or error_position > len(values):
        raise ValueError("ECC 纠错失败：错误位置无效")

    index = error_position - 1
    repaired_value = (values[index] - symbol_sum) % field_size
    values[index] = repaired_value

    if not ecc_block_is_valid(values, field_size):
        raise ValueError("ECC 纠错失败：校验未通过")


def ecc_block_is_valid(values: list[int | None], field_size: int = ECC_FIELD_SIZE) -> bool:
    symbol_sum = sum(value for value in values if value is not None) % field_size
    weighted_sum = sum(
        (i + 1) * value
        for i, value in enumerate(values)
        if value is not None
    ) % field_size
    return symbol_sum == 0 and weighted_sum == 0


def encrypt(data: bytes, password: str, use_ecc: bool = False,
            use_sutra: bool = False) -> str:
    salt = os.urandom(16)
    nonce = os.urandom(12)

    key = derive_key(password, salt)
    aesgcm = AESGCM(key)

    ciphertext = aesgcm.encrypt(
        nonce,
        data,
        None
    )

    payload = salt + nonce + ciphertext
    if not use_sutra:
        body = base64.urlsafe_b64encode(payload).decode("ascii").rstrip("=")
        return encode_ecc_body(body, BASE64_ALPHABET, BASE64_ECC_ALPHABET) if use_ecc else body
    if use_ecc:
        return bytes_to_ecc_sutra(payload)
    return bytes_to_sutra(payload)


def decrypt(text: str, password: str) -> bytes:
    if not text.startswith(PREFIX):
        try:
            return decrypt_payload(base64_to_bytes(text), password)
        except (ValueError, InvalidTag):
            repaired = decode_ecc_body(text, BASE64_ALPHABET, BASE64_ECC_ALPHABET)
            return decrypt_payload(base64_to_bytes(repaired), password)
    try:
        return decrypt_payload(sutra_to_bytes(text), password)
    except (ValueError, InvalidTag) as normal_error:
        try:
            return decrypt_payload(ecc_sutra_to_bytes(text), password)
        except (ValueError, InvalidTag):
            raise normal_error


def base64_to_bytes(text: str) -> bytes:
    if not text or any(ch not in BASE64_ALPHABET for ch in text):
        raise ValueError("不是有效的 Base64 密文")
    payload = base64.b64decode(text + "=" * (-len(text) % 4), altchars=b"-_", validate=True)
    if base64.urlsafe_b64encode(payload).decode("ascii").rstrip("=") != text:
        raise ValueError("Base64 密文格式损坏")
    return payload


def decrypt_payload(payload: bytes, password: str) -> bytes:
    if len(payload) < 44:
        raise ValueError("密文长度不足")
    salt = payload[:16]
    nonce = payload[16:28]
    ciphertext = payload[28:]

    key = derive_key(password, salt)
    aesgcm = AESGCM(key)

    return aesgcm.decrypt(nonce, ciphertext, None)


def parse_args(argv: list[str]) -> ParsedArgs:
    mode = "encrypt"
    mode_set = False
    output_path = None
    inputs = []
    ecc = False
    sutra = False
    literal_text = False
    recursive = False
    delete_source = False

    i = 0
    while i < len(argv):
        arg = argv[i]

        if arg == "--":
            inputs.extend(argv[i + 1:])
            literal_text = True
            break
        elif arg in ("-encrypt", "-decrypt"):
            new_mode = arg[1:]
            if mode_set and mode != new_mode:
                raise ValueError("-encrypt 和 -decrypt 不能同时使用")
            mode = new_mode
            mode_set = True
        elif arg == "-ecc":
            ecc = True
        elif arg == "-sutra":
            sutra = True
        elif arg == "-recursive":
            recursive = True
        elif arg == "-delete-source":
            delete_source = True
        elif arg == "-o":
            i += 1
            if i >= len(argv):
                raise ValueError("-o 后必须指定输出路径和文件名")
            output_path = argv[i]
            if output_path.startswith("-"):
                raise ValueError("-o 后必须指定输出路径和文件名")
        elif arg.startswith("-"):
            raise ValueError(f"未知参数：{arg}")
        else:
            inputs.append(arg)

        i += 1

    if recursive:
        if mode != "encrypt" or literal_text or len(inputs) != 1:
            raise ValueError("-recursive 仅用于加密一个目录")
        input_path = Path(inputs[0]).expanduser()
        if input_path.is_symlink() or not input_path.is_dir():
            raise ValueError("-recursive 必须指定真实目录")
    else:
        input_path = None if literal_text else resolve_input_file(inputs)
    if delete_source and (mode != "encrypt" or input_path is None):
        raise ValueError("-delete-source 仅用于文件或目录加密")
    if delete_source and input_path.is_symlink():
        raise ValueError("-delete-source 不支持符号链接")
    text = None if input_path else " ".join(inputs) if inputs else None
    return ParsedArgs(mode, output_path, text, input_path, ecc, sutra,
                      recursive, delete_source)


def resolve_input_file(inputs: list[str]) -> Path | None:
    if len(inputs) != 1:
        return None

    input_path = Path(inputs[0]).expanduser()
    if not input_path.exists():
        if input_path.suffix.lower() in SUPPORTED_TEXT_SUFFIXES or any(
            separator in inputs[0] for separator in ("/", "\\")
        ):
            raise ValueError(f"输入文件不存在：{input_path}")
        return None
    if not input_path.is_file():
        raise ValueError(f"输入路径不是文件，目录加密需显式指定 -recursive：{input_path}")

    suffix = input_path.suffix.lower()
    if suffix not in SUPPORTED_TEXT_SUFFIXES:
        supported = " ".join(sorted(SUPPORTED_TEXT_SUFFIXES))
        raise ValueError(f"不支持的文件格式：{suffix or '无后缀'}。支持：{supported}")

    return input_path


def read_input_file(input_path: Path) -> bytes:
    return input_path.read_bytes()


def read_stdin_bytes() -> bytes:
    return sys.stdin.buffer.read()


def ciphertext_bytes_to_text(data: bytes) -> str:
    if data.endswith(b"\n"):
        data = data[:-1]
    if data.endswith(b"\r"):
        data = data[:-1]
    return data.decode("utf-8")


def resolve_output_path(output_path: str | None, force_file: bool) -> Path | None:
    if output_path:
        return Path(output_path).expanduser()
    if force_file:
        return DEFAULT_FILE_OUTPUT
    return None


def write_text_output(text: str, output_path: Path | None) -> None:
    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(text, encoding="utf-8")
    else:
        print(text)


def write_bytes_output(data: bytes, output_path: Path | None) -> None:
    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(data)
    else:
        sys.stdout.buffer.write(data)


def directory_jobs(source: Path, destination: Path,
                   in_place: bool = False) -> list[tuple[Path, Path]]:
    source = source.resolve()
    destination = destination.resolve()
    if (destination == source and not in_place) or source in destination.parents:
        raise ValueError("输出目录不能位于输入目录内")
    jobs = []
    def walk_error(error):
        raise error

    for current, directories, filenames in os.walk(source, onerror=walk_error):
        current = Path(current)
        directories[:] = sorted(name for name in directories
                                if not (current / name).is_symlink())
        for name in sorted(filenames):
            path = current / name
            if path.is_symlink() or not path.is_file():
                continue
            if in_place and name.endswith(".encrypted.txt"):
                continue
            relative = path.relative_to(source)
            output = destination / relative.parent / (relative.name + ".encrypted.txt")
            if output.exists() or output.is_symlink():
                raise ValueError(f"输出文件已存在：{output}")
            # Reject redirected output subdirectories before any files are processed.
            if destination not in output.resolve().parents:
                raise ValueError(f"输出路径越过输出目录：{output}")
            for parent in output.parents:
                if parent.exists() and not parent.is_dir():
                    raise ValueError(f"输出路径的父级不是目录：{parent}")
            jobs.append((path, output))
    return jobs


def encrypt_file(source: Path, output: Path, password: str, args: ParsedArgs) -> None:
    if source.is_symlink() or not source.is_file():
        raise ValueError(f"输入不是普通文件：{source}")
    if source.resolve() == output.resolve():
        raise ValueError("输出文件不能与原文件相同")
    before = source.stat()
    data = source.read_bytes()
    result = encrypt(data, password, args.ecc, args.sutra)
    output.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive creation protects existing ciphertext and hard links to source files.
    with output.open("xb") as stream:
        stream.write(result.encode("utf-8"))
        stream.flush()
        os.fsync(stream.fileno())
    if args.delete_source:
        if decrypt(output.read_bytes().decode("utf-8"), password) != data:
            raise ValueError(f"密文回读验证失败，保留原文件：{source}")
        after = source.stat()
        if (source.is_symlink() or
                (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns,
                 before.st_ctime_ns) !=
                (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns,
                 after.st_ctime_ns) or source.read_bytes() != data):
            raise ValueError(f"原文件在处理期间发生变化，保留原文件：{source}")
        source.unlink()


def main() -> None:
    try:
        args = parse_args(sys.argv[1:])
    except ValueError as exc:
        print(exc)
        sys.exit(2)

    if args.recursive:
        in_place = args.delete_source and args.output_path is None
        destination = (Path(args.output_path).expanduser() if args.output_path
                       else args.input_path if in_place
                       else Path.home() / "Desktop" / "out")
        jobs = directory_jobs(args.input_path, destination, in_place)
        if not jobs:
            print("目录中没有可加密的普通文件")
            return
        password = getpass("请输入密码: ")
        for source, output in jobs:
            encrypt_file(source, output, password, args)
        print(f"已加密 {len(jobs)} 个文件，输出目录：{destination}")
        return

    output_path = resolve_output_path(args.output_path, args.input_path is not None)

    if args.delete_source:
        password = getpass("请输入密码: ")
        encrypt_file(args.input_path, output_path, password, args)
        return

    if args.mode == "encrypt":
        data = read_input_file(args.input_path) if args.input_path else None
        if data is None and args.text is not None:
            data = args.text.encode("utf-8")
        if data is None:
            if sys.stdin.isatty():
                data = input("请输入要加密的内容: ").encode("utf-8")
            else:
                data = read_stdin_bytes()

        password = getpass("请输入密码: ")

        result = encrypt(data, password, args.ecc, args.sutra)
        write_text_output(result, output_path)

    elif args.mode == "decrypt":
        text = (
            ciphertext_bytes_to_text(read_input_file(args.input_path))
            if args.input_path
            else args.text
        )
        if text is None:
            if sys.stdin.isatty():
                text = input("请输入密文: ")
            else:
                text = ciphertext_bytes_to_text(read_stdin_bytes())

        password = getpass("请输入密码: ")

        try:
            result = decrypt(text, password)
            write_bytes_output(result, output_path)
        except Exception:
            print("解密失败：密码错误，或密文内容被篡改。")
            sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError) as exc:
        print(f"操作失败：{exc}", file=sys.stderr)
        sys.exit(1)
