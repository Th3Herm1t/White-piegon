"""Test SKU parsing on actual XLSX data"""
from config import parse_sku
import pandas as pd

df = pd.read_excel('FILLETTE  V3.xlsx', header=None)

# Collect all SKUs and their parses
sku_groups = {}

for i in range(4, min(100, len(df))):
    raw_sku = df.iloc[i, 2]
    if pd.isna(raw_sku):
        continue
    
    base_sku, var_code = parse_sku(raw_sku)
    if base_sku:
        if base_sku not in sku_groups:
            sku_groups[base_sku] = []
        sku_groups[base_sku].append({
            'row': i,
            'raw_sku': str(raw_sku),
            'var_code': var_code,
            'color': df.iloc[i, 6] if pd.notna(df.iloc[i, 6]) else None
        })

# Save to file
with open('sku_analysis.txt', 'w', encoding='utf-8') as f:
    f.write("=" * 80 + "\n")
    f.write("SKU PARSING ANALYSIS\n")
    f.write("=" * 80 + "\n\n")
    
    f.write(f"Total base SKUs: {len(sku_groups)}\n")
    f.write(f"Total rows with valid SKU: {sum(len(v) for v in sku_groups.values())}\n\n")
    
    f.write("Grouped by Base SKU:\n")
    f.write("-" * 80 + "\n")
    
    for base_sku, variants in sorted(sku_groups.items()):
        f.write(f"\n{base_sku} ({len(variants)} variant(s)):\n")
        for v in variants:
            var_str = v['var_code'] if v['var_code'] else 'None'
            color_str = v['color'] if v['color'] else 'None'
            f.write(f"  Row {v['row']}: {v['raw_sku']:35} var={var_str:15} color={color_str}\n")

print("Analysis saved to sku_analysis.txt")
