#!/usr/bin/env python
"""Verify merged index file."""
import pandas as pd

df = pd.read_parquet('indexes/merged_index.parquet')
print(f'✅ 合并索引总行数: {len(df):,}')
print(f'\n📊 数据来源分布:')
for src, cnt in df['source'].value_counts().items():
    print(f'  {src}: {cnt:,}')

print(f'\n📋 列名: {list(df.columns)}')
print(f'\n📝 前 5 条样例:')
key_cols = [c for c in ['source', 'formula', 'elements', 'nelements', 'spacegroup', 'path'] if c in df.columns]
print(df[key_cols].head(5).to_string(index=False))

# Check for missing critical fields
print(f'\n⚠️  数据完整性检查:')
for col in ['formula', 'elements', 'path']:
    if col in df.columns:
        missing = df[col].isna().sum()
        pct = missing / len(df) * 100
        print(f'  {col}: {missing:,} missing ({pct:.1f}%)')
