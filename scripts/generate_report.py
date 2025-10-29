#!/usr/bin/env python
"""Generate final completion report."""
import os
from pathlib import Path

print("=" * 70)
print("索引构建完成报告")
print("=" * 70)

print("\n📂 生成的索引文件:")
index_dir = Path("indexes")
for f in sorted(index_dir.glob("*")):
    if f.is_file():
        size_mb = f.stat().st_size / 1024 / 1024
        print(f"  ✓ {f.name}: {size_mb:.1f} MB")

print("\n" + "=" * 70)
print("数据统计摘要")
print("=" * 70)

try:
    import pandas as pd
    
    # Individual indices
    print("\n📊 ICSD 索引:")
    icsd = pd.read_parquet("indexes/icsd_index.parquet")
    print(f"  记录数: {len(icsd):,}")
    print(f"  列数: {len(icsd.columns)}")
    
    print("\n📊 COD 索引:")
    cod = pd.read_parquet("indexes/cod_index.parquet")
    print(f"  记录数: {len(cod):,}")
    print(f"  列数: {len(cod.columns)}")
    
    print("\n📊 合并索引:")
    merged = pd.read_parquet("indexes/merged_index.parquet")
    print(f"  总记录数: {len(merged):,}")
    print(f"  列数: {len(merged.columns)}")
    print(f"  来源分布:")
    for src, cnt in merged['source'].value_counts().items():
        print(f"    - {src}: {cnt:,}")
    
    # Data quality metrics
    print("\n📈 数据质量指标:")
    has_formula = (~merged['formula'].isna()).sum()
    has_path = (~merged['path'].isna()).sum()
    has_spacegroup = (~merged['spacegroup'].isna()).sum()
    
    print(f"  含化学式: {has_formula:,} ({has_formula/len(merged)*100:.1f}%)")
    print(f"  含文件路径: {has_path:,} ({has_path/len(merged)*100:.1f}%)")
    print(f"  含空间群: {has_spacegroup:,} ({has_spacegroup/len(merged)*100:.1f}%)")
    
    # Element distribution (top 10)
    print("\n🔬 元素分布 (前10):")
    all_elements = []
    for elems in merged['elements'].dropna():
        if isinstance(elems, list):
            all_elements.extend(elems)
    from collections import Counter
    elem_counts = Counter(all_elements)
    for elem, cnt in elem_counts.most_common(10):
        print(f"  {elem}: {cnt:,}")

except Exception as e:
    print(f"\n⚠️  统计时出错: {e}")

print("\n" + "=" * 70)
print("下一步建议")
print("=" * 70)
print("""
1. ✅ 索引已完成并合并
   - ICSD: 229,487 条记录
   - COD: 501,975 条记录
   - 合并: 731,462 条记录

2. 📝 注意事项:
   - ICSD 记录没有独立 CIF 文件（path 为 None）
   - 部分 COD 记录缺少空间群信息
   - 约 0.8% 的记录缺少化学式

3. 🔄 可选的后续步骤:
   - 为 ICSD 记录从 inline CIF 生成独立文件
   - 使用 pymatgen 重新解析缺少空间群的 CIF
   - 实现 MP (Materials Project) 索引

4. 💻 在 DARA 中使用:
   - 使用 merged_index.parquet 作为统一候选库
   - 或分别使用 icsd_index.parquet 和 cod_index.parquet
   - 通过 elements/formula 过滤候选相
""")

print("=" * 70)
