# GameTrix：直接增加 40 张操作牌

本实验完整保留原有 97 张牌：12 张蓝牌、30 张红牌、40 张操作牌、15 张主目标牌。另加 40 张操作牌，总牌数 137，操作牌堆 80。红牌、蓝牌、目标条件和原操作没有改动。

| 新牌 | 编号 | 张数 | 效果 | 红牌费用 |
|---|---|---:|---|---|
| 单格 ±1 | O41–O64 | 24 | 任意现有一格加 1 或减 1 | 任意一张，不限形状/数值 |
| 单格清零 | O65–O72 | 8 | 任意现有一格变成 0 | 任意一张，不限形状/数值 |
| 内部行列相加减 | O73–O80 | 8 | 当前矩阵中，一行/列加减另一条不同的行/列；来源不变 | 无 |

单格操作消耗红牌作为材料，不读取它的数值。内部行列相加减的系数只能为 +1 或 −1。所有其他位置保持不变，尺寸不变。单格清零可作用于已为零的位置；与原型中其他合法但不改变结果的操作一样，它仍消耗牌并被记录。

仍为每回合抽 3 张操作牌、5 张红牌，未用牌全部保留，每回合至少执行一次操作。没有删牌、替换旧牌，也没有新增红牌或改动其生成方式。

可打印文件：

- [仅新增的 40 张操作牌](generated/extra_operations.html)
- [完整的 137 张牌](generated/cards.html)
- [机器可读扩展牌组](generated/deck.json)
- [冻结的原版对照牌组](generated/baseline_deck.json)

从 GameTrix 目录启动一局带相同计算预算、固定 8 回合上限的新实验：

```sh
python3 student_play.py start expansion_v1/playtests/my_trial.json --deck expansion_v1/generated/deck.json --seed 101 --objective C01 --blue B01 --fixed-horizon
python3 student_play.py show expansion_v1/playtests/my_trial.json
```

新操作的 `plan` 参数：

```text
entry_tweak:    --red Rxx --i 行下标 --j 列下标 --delta 1或-1
entry_zero:     --red Rxx --i 行下标 --j 列下标
combine_vectors: --axis row或column --source 来源下标 --target 目标下标 --delta 1或-1
```

下标从 0 开始，`--operation` 使用手里实际的物理卡 ID。完整命令和计算限制见 [PROTOCOL.md](PROTOCOL.md)。

实验预先选定六组目标/蓝牌/种子，原版与扩展版各六局，每组由互不看对方解法的新代理游玩。都采用每回合最多两个候选、一次预算，每局最多六次预算；执行到胜利或完整八回合上限。停止原因和未获胜案例保留。配置见 [manifest.json](manifest.json)。

由于牌堆由 40 增至 80，即使种子相同，抽牌序列也不同。新增牌更常见，同时原有特定操作更难抽到。实验比较的是整套扩展，而非单独某一种操作的因果作用；少量代理试玩也不能代替真人数据。

生成器为 `expansion.py`，只追加新牌。另选新输出目录可重新导出，既有文件不会被覆盖：

```sh
python3 expansion.py --base generated/deck.json --out expansion_copy
```
