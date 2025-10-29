#!/usr/bin/env python3
"""验证 MP 索引完成情况"""

import pandas as pd
from pathlib import Path

print("========================================")
print("📊 MP 索引完成统计")
print("========================================\n")

# 加载索引
df = pd.read_parquet('indexes/mp_index.parquet')

# 基础统计
print(f"总记录数: {len(df):,}")
print(f"\n实验/理论分布:")
print(f"  实验结构: {len(df[df['experimental_status']=='experimental']):,} ({100*len(df[df['experimental_status']=='experimental'])/len(df):.1f}%)")
print(f"  理论结构: {len(df[df['experimental_status']=='theoretical']):,} ({100*len(df[df['experimental_status']=='theoretical'])/len(df):.1f}%)")

# 数据覆盖
print(f"\n数据覆盖率:")
print(f"  空间群: {df['spacegroup'].notna().sum():,} ({100*df['spacegroup'].notna().sum()/len(df):.1f}%)")
print(f"  CIF 路径: {df['path'].notna().sum():,} ({100*df['path'].notna().sum()/len(df):.1f}%)")
print(f"  能量数据: {df['energy_above_hull'].notna().sum():,} ({100*df['energy_above_hull'].notna().sum()/len(df):.1f}%)")

# CIF 文件数量
cif_dir = Path('mp_cifs')
if cif_dir.exists():
    cif_count = sum(1 for _ in cif_dir.rglob('*.cif'))
    print(f"\nCIF 文件数量: {cif_count:,}")
else:
    print(f"\n⚠️ CIF 目录不存在: {cif_dir}")

# 索引文件大小
parquet_path = Path('indexes/mp_index.parquet')
if parquet_path.exists():
    parquet_size = parquet_path.stat().st_size / 1024 / 1024
    print(f"索引文件大小: {parquet_size:.2f} MB")

# 示例数据
print(f"\n示例数据（前 3 条）:")
print(df[['raw_db_id', 'formula', 'spacegroup', 'experimental_status', 'energy_above_hull']].head(3))

print("\n========================================")
print("✅ 验证完成！")
print("========================================")
