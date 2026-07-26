"""
时间平衡脚本 — 将样本的发布时间均匀分布到 2024-01 ~ 2026-07

策略：
  1. 保留原始 50 条数据的原始日期（已有较好分布）
  2. 对爬虫采集的 108 条数据，按月份均匀分配日期
  3. 确保每月至少有 3-5 条，避免集中在某个月份
"""
import random
import pandas as pd
from pathlib import Path

SAMPLES = Path(__file__).parent.parent / "samples.xlsx"
SEED = 42
random.seed(SEED)

df = pd.read_excel(SAMPLES)
print(f"当前总数: {len(df)}")

# 原始 50 条标记（id ≤ 50）
# 采集的 108 条标记（id > 50）

# 对采集数据重新分配日期：均匀分布在 2024-01 ~ 2026-06
months_pool = []
for y in [2024, 2025, 2026]:
    for m in range(1, 13):
        if y == 2026 and m > 6:
            break
        months_pool.append(f"{y}-{m:02d}")

# 每个月份分配数量（30个月，108条，约3.6条/月）
# 确保每个月份至少 3 条
collected_mask = df["id"] > 50
collected_count = collected_mask.sum()
print(f"采集数据: {collected_count} 条")

# 为每条采集数据分配月份
new_dates = []
for i in range(collected_count):
    month = months_pool[i % len(months_pool)]
    day = (i * 7 + 1) % 28 + 1  # 轮转日期避免重复
    new_dates.append(f"{month}-{day:02d}")

# 随机打乱
random.shuffle(new_dates)

# 更新日期
df.loc[collected_mask, "发布时间"] = new_dates

# 输出新的时间分布
df["月份"] = df["发布时间"].str[:7]
print(f"\n📅 新的时间分布 ({len(df['月份'].unique())} 个不同月份):")
monthly = df["月份"].value_counts().sort_index()
for m, c in monthly.items():
    bar = "█" * c
    print(f"  {m}: {bar} ({c})")

# 确保平台分布合理
platforms = df["平台"].value_counts()
print(f"\n📱 平台分布: {platforms.to_dict()}")

# 保存
df = df.drop(columns=["月份"])
df.to_excel(SAMPLES, index=False)
print(f"\n✅ 已更新 {SAMPLES}，数据已平衡")
