"""
Validate XLSX to Image Folder Matching

This script analyzes all XLSX SKUs and shows which would match
to image folders (if folders existed with expected naming).

RUN THIS BEFORE IMPORTING TO STORE!
"""

import os
import pandas as pd
from config import XLSX_COLUMNS, XLSX_DATA_START_ROW
from image_mapping import normalize_sku, scan_image_folders, find_images_for_sku

# Read XLSX
df = pd.read_excel('FILLETTE  V3.xlsx', header=None)

# Build list of all SKUs with normalization info
all_skus = []
for i in range(XLSX_DATA_START_ROW, len(df)):
    raw_sku = df.iloc[i, XLSX_COLUMNS['sku']]
    if pd.isna(raw_sku):
        continue
    
    raw = str(raw_sku).strip()
    normalized, base_sku, var_code = normalize_sku(raw)
    
    all_skus.append({
        'row': i,
        'raw_sku': raw,
        'normalized': normalized,
        'base_sku': base_sku,
        'var_code': var_code,
        'expected_folder': normalized.upper() if normalized else None
    })

# Scan image folders
folder_map = scan_image_folders()

# Match each SKU to images
matched = []
unmatched = []

for sku_info in all_skus:
    images = find_images_for_sku(sku_info['raw_sku'], folder_map)
    sku_info['images'] = images
    sku_info['image_count'] = len(images)
    
    if images:
        matched.append(sku_info)
    else:
        unmatched.append(sku_info)

# Generate report
print("=" * 100)
print("XLSX TO IMAGE FOLDER VALIDATION REPORT")
print("=" * 100)

print(f"\nTotal XLSX SKUs: {len(all_skus)}")
print(f"Available image folders: {len(folder_map)}")
print(f"SKUs with matching images: {len(matched)}")
print(f"SKUs without images: {len(unmatched)}")
print(f"\nMatch rate: {len(matched) / len(all_skus) * 100:.1f}%")

print("\n" + "=" * 100)
print("MATCHED SKUs (have images)")
print("=" * 100)

if matched:
    for s in matched[:20]:
        print(f"  Row {s['row']}: {s['raw_sku']:<35} -> {s['image_count']} images")
    if len(matched) > 20:
        print(f"  ... and {len(matched) - 20} more")
else:
    print("  (none)")

print("\n" + "=" * 100)
print("UNMATCHED SKUs (no images found)")
print("=" * 100)

# Group unmatched by expected folder pattern
print("\nExpected folder names for unmatched SKUs (first 30):")
for s in unmatched[:30]:
    print(f"  Row {s['row']}: {s['raw_sku']:<35} -> expected folder: {s['expected_folder']}")

# Show what folders ARE available
print("\n" + "=" * 100)
print("AVAILABLE IMAGE FOLDERS (downloaded)")
print("=" * 100)

for key, info in sorted(folder_map.items()):
    matched_count = sum(1 for s in matched if s.get('expected_folder', '').upper() == key)
    print(f"  {info['name']:<30} ({len(info['images'])} images) - matches {matched_count} XLSX rows")

# Summary of what's needed
print("\n" + "=" * 100)
print("SUMMARY & RECOMMENDATIONS")
print("=" * 100)

print(f"""
CURRENT STATE:
- {len(unmatched)} of {len(all_skus)} XLSX products are missing images
- Only {len(folder_map)} image folders downloaded (gdown hit permission limits)

TO COMPLETE IMAGE IMPORT:
1. Download ALL image folders from Google Drive manually:
   - Go to: https://drive.google.com/drive/folders/1QgS-z9KebWWiV10Otaa4vwUSRFOu16og
   - Right-click -> Download (will create a ZIP)
   - Extract to: ./images/

2. Expected folder naming (based on XLSX SKUs):
""")

# Show unique expected folder patterns
unique_patterns = sorted(set(s['expected_folder'] for s in all_skus if s['expected_folder']))
print(f"   Total unique folder names expected: {len(unique_patterns)}")
print("   Examples:")
for p in unique_patterns[:10]:
    print(f"     - {p}")

# Save detailed report
with open('image_validation_report.txt', 'w', encoding='utf-8') as f:
    f.write("XLSX TO IMAGE FOLDER VALIDATION REPORT\n")
    f.write("=" * 100 + "\n\n")
    
    f.write(f"Total XLSX SKUs: {len(all_skus)}\n")
    f.write(f"Available image folders: {len(folder_map)}\n")
    f.write(f"SKUs with matching images: {len(matched)}\n")
    f.write(f"SKUs without images: {len(unmatched)}\n\n")
    
    f.write("ALL XLSX SKUs AND EXPECTED FOLDERS:\n")
    f.write("-" * 100 + "\n")
    f.write(f"{'Row':<6} {'Raw SKU':<35} {'Expected Folder':<35} {'Status':<15}\n")
    f.write("-" * 100 + "\n")
    
    for s in all_skus:
        status = f"{s['image_count']} images" if s['image_count'] > 0 else "NO MATCH"
        f.write(f"{s['row']:<6} {s['raw_sku']:<35} {s['expected_folder'] or 'N/A':<35} {status:<15}\n")

print("\n\nDetailed report saved to: image_validation_report.txt")
