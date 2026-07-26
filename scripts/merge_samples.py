"""合并原始样本与采集样本"""
import pandas as pd

orig = pd.read_excel("samples.xlsx")
new = pd.read_excel("data/collected_samples.xlsx")

# 去重
titles = set(orig["标题"].tolist())
new_unique = new[~new["标题"].isin(titles)]
print(f"原始: {len(orig)} 条, 新增: {len(new_unique)} 条")

# 合并重编号
merged = pd.concat([orig, new_unique], ignore_index=True)
merged["id"] = range(1, len(merged) + 1)
merged = merged[["id", "标题", "标签/类别", "平台", "发布时间", "来源", "内容摘要"]]
merged.to_excel("samples.xlsx", index=False)

print(f"合并后: {len(merged)} 条")
print(f"类别: {merged['标签/类别'].value_counts().to_dict()}")
print(f"平台: {merged['平台'].value_counts().to_dict()}")
