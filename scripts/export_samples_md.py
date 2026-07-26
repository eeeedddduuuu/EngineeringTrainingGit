"""导出 samples.xlsx → Markdown（Coze 知识库可上传）"""
import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
df = pd.read_excel(ROOT / "samples.xlsx")

OUT = ROOT / "data" / "samples_for_coze.md"
OUT.parent.mkdir(parents=True, exist_ok=True)

with open(OUT, "w", encoding="utf-8") as f:
    f.write("# 爆款内容样例库\n\n")
    f.write(
        f"共 {len(df)} 条样例数据，覆盖游戏策划、短视频创作、宣传片制作、社交媒体运营四大类别。\n\n"
    )

    for _, r in df.iterrows():
        f.write("---\n")
        f.write(f"标题: {r['标题']}\n")
        f.write(f"标签: {r['标签/类别']}\n")
        f.write(f"平台: {r['平台']}\n")
        f.write(f"发布时间: {r['发布时间']}\n")
        f.write(f"来源: {r['来源']}\n")
        f.write(f"摘要: {r['内容摘要']}\n")
        f.write("\n")

print(f"Done: {OUT}  ({len(df)} entries)")
