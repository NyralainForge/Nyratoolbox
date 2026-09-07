# Random Dice

一个仅依赖 Python 标准库的随机数与组合骰子命令行工具。支持普通骰子、自定义整数区间、分组小计和固定加值，也可以作为 Python 模块调用。

## 运行要求

- Python 3.9+
- 无需安装第三方依赖

以下命令均在仓库根目录执行。

## 快速开始

```bash
# 默认投掷 1D10，固定加值为 0
python3 random_dice/random_dice.py

# 两颗六面骰加一颗四面骰，最后统一加 3
python3 random_dice/random_dice.py '2D6+1D4' --modifier 3

# 在 [-3, 8] 内生成两个整数，再投掷一颗二十面骰
python3 random_dice/random_dice.py '2[-3,8]+1D20'

# 固定减值，只输出最终总和
python3 random_dice/random_dice.py '1D20' -m -2 --total-only

# 结构化输出
python3 random_dice/random_dice.py '2D6+1D4' --json

# 查看帮助
python3 random_dice/random_dice.py --help
```

## 表达式语法

| 写法 | 含义 |
| --- | --- |
| `NDM` | 生成 N 个介于 1 和 M 之间的整数，如 `2D6` |
| `N[min,max]` | 在指定闭区间内生成 N 个整数，如 `2[-3,8]` |
| `组1+组2` | 合并多组结果，如 `2D6+1D4+2[-3,8]` |

- `D` 不区分大小写，表达式内的空白会被移除。
- 所有区间均包含两端，允许最小值等于最大值；结果允许重复，不去重。
- 普通骰子面数至少为 1；自定义区间支持负整数和 0。
- 固定加减值通过 `--modifier` 传入，只对所有随机数的总和加一次。
- 不支持 `D6` 省略数量、`2D6+3` 直接加常数、`2D6-1`、乘除、括号或小数。请用 `1D6`、`2D6 -m 3`、`2D6 -m -1` 等写法。
- 自定义区间的正整数不带 `+` 前缀，例如使用 `1[1,6]`。
- 建议将表达式放在引号内，尤其含 `[]` 时，避免被 shell 当作文件匹配模式。

### 输入限制

| 项目 | 限制 |
| --- | --- |
| 表达式长度 | 去除空白后最多 512 个字符 |
| 分组数量 | 每次最多 20 组 |
| 随机数数量 | 每组至少 1 个，所有组合计最多 10,000 个 |
| 自定义区间 | 最小值 ≤ 最大值，两端均在 ±1,000,000,000,000 内 |
| 普通骰子面数 | 1 至 1,000,000,000,000 |
| 固定加值 | ±1,000,000,000,000 内的整数 |

表达式中的数量最多写 5 位数字，面数和区间端点最多写 13 位数字（不含负号）；多余的前导零也计入位数限制。固定加值的数字部分同样最多 13 位。总和不受单个区间端点的上限限制。

## 命令行参数

| 参数 | 说明 | 默认值 |
| --- | --- | --- |
| `expression` | 可选的位置参数，指定骰子组合 | `1D10` |
| `-m` / `--modifier` | 固定加值，可以为负数 | `0` |
| `--json` | 输出一行 JSON | 关闭 |
| `--total-only` | 只输出最终总和 | 关闭 |
| `-h` / `--help` | 显示帮助 | — |

`--json` 和 `--total-only` 互斥。结果写入标准输出，不会自动创建文件；可使用 shell 重定向保存：

```bash
python3 random_dice/random_dice.py '2D6' --json > result.json
```

成功执行返回退出码 `0`；参数或表达式无效时，错误信息写入标准错误并返回 `2`。

## 输出示例

为便于复现，以下使用固定区间 `2[3,3]+1D1`，并传入 `-m -2`：

```text
组合：2[3,3]+1D1
2[3,3]: 3, 3  小计 6
1D1: 1  小计 1
随机数合计：7
固定加值：-2（仅加一次）
总和：5
```

相同参数配合 `--json` 会输出以下数据（为便于阅读，此处已换行）：

```json
{
  "expression": "2[3,3]+1D1",
  "groups": [
    {"expression": "2[3,3]", "values": [3, 3], "subtotal": 6},
    {"expression": "1D1", "values": [1], "subtotal": 1}
  ],
  "count": 3,
  "subtotal": 7,
  "modifier": -2,
  "total": 5
}
```

`expression` 为规范化后的组合；`groups` 按输入顺序保留每组结果及小计；`count` 为随机数总个数；`subtotal` 不含固定加值；`total = subtotal + modifier`。`--total-only` 在此示例中仅输出 `5`。

## 在 Python 中调用

在仓库根目录运行 Python 时，可以直接导入：

```python
from random_dice.random_dice import roll

result = roll("2D6+1[-2,4]", modifier="3")
print(result["groups"])
print(result["total"])
```

`roll(expression="1D10", modifier="0")` 返回与 JSON 输出相同结构的字典；输入无效时抛出 `ValueError`。

文件还保留了供其他程序或网页后端复用的函数：

- `generate_random_numbers(form)`：接收字符串字段 `minimum`、`maximum`、`count`，返回随机整数列表。可选的 `sum` 只接受空字符串或 `"yes"`，函数本身不执行求和。
- `generate_random_result(form)`：返回 `(numbers, groups, modifier)`。提供 `expression` 时解析组合；省略该字段时使用上述区间字段，返回的 `groups` 为 `None`。显式传入空表达式会报错。返回的随机数尚未加上固定加值。

当前目录仅提供命令行工具与计算函数，不包含网页界面或 HTTP 服务。文件中的 `PRESETS` 为预设映射常量，命令行没有预设选择参数。

## 随机数来源

使用标准库 `secrets.randbelow` 从每组闭区间内均匀抽取整数。工具未提供随机种子设置，因此普通随机结果不能通过指定 seed 重放。
