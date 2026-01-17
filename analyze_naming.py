"""
Analyze naming consistency between XLSX SKUs and Google Drive folder names.

This script compares:
1. SKU patterns from XLSX (parsed to folder-style names)
2. Actual folder names downloaded from Google Drive
"""

import os
import pandas as pd
import re
from config import parse_sku, XLSX_COLUMNS, XLSX_DATA_START_ROW

# Read XLSX
df = pd.read_excel('FILLETTE  V3.xlsx', header=None)

# Get all SKUs and their normalized forms
xlsx_skus = []
for i in range(XLSX_DATA_START_ROW, len(df)):
    raw_sku = df.iloc[i, XLSX_COLUMNS['sku']]
    if pd.isna(raw_sku):
        continue
    
    raw = str(raw_sku).strip()
    base_sku, var_code = parse_sku(raw_sku)
    
    # Normalize to folder format (remove spaces, keep hyphen with var code)
    if base_sku and var_code:
        folder_style = f"{base_sku.replace(' ', '')}-{var_code}"
    elif base_sku:
        folder_style = base_sku.replace(' ', '')
    else:
        folder_style = raw.replace(' ', '')
    
    xlsx_skus.append({
        'row': i,
        'raw_sku': raw,
        'base_sku': base_sku,
        'var_code': var_code,
        'folder_style': folder_style
    })

# Get downloaded folder names
images_dir = './images'
downloaded_folders = []
if os.path.exists(images_dir):
    downloaded_folders = [f for f in os.listdir(images_dir) if os.path.isdir(os.path.join(images_dir, f))]

# Analysis
print("=" * 80)
print("NAMING CONSISTENCY ANALYSIS")
print("=" * 80)

print(f"\nXLSX rows with SKUs: {len(xlsx_skus)}")
print(f"Downloaded image folders: {len(downloaded_folders)}")

# Show downloaded folders
print("\n--- Downloaded Folders ---")
for f in sorted(downloaded_folders):
    print(f"  {f}")

# Show XLSX SKU patterns (first 30)
print("\n--- XLSX SKU Patterns (first 30) ---")
print(f"{'Row':<6} {'Raw SKU':<30} {'Folder Style':<30}")
print("-" * 66)
for s in xlsx_skus[:30]:
    print(f"{s['row']:<6} {s['raw_sku']:<30} {s['folder_style']:<30}")

# Check for potential issues
print("\n--- Potential Naming Issues ---")

issues = []

# Issue 1: Spaces in SKUs
skus_with_spaces = [s for s in xlsx_skus if ' ' in s['raw_sku']]
if skus_with_spaces:
    issues.append({
        'type': 'Spaces in raw SKU',
        'count': len(skus_with_spaces),
        'examples': [s['raw_sku'] for s in skus_with_spaces[:5]]
    })

# Issue 2: Inconsistent separators (space-dash vs just dash)
dash_patterns = {}
for s in xlsx_skus:
    raw = s['raw_sku']
    if ' -' in raw:
        pattern = 'space-dash'
    elif '- ' in raw:
        pattern = 'dash-space'
    elif '-' in raw:
        pattern = 'just-dash'
    else:
        pattern = 'no-dash'
    dash_patterns[pattern] = dash_patterns.get(pattern, 0) + 1

if len(dash_patterns) > 1:
    issues.append({
        'type': 'Inconsistent dash patterns',
        'count': len(dash_patterns),
        'examples': list(dash_patterns.items())
    })

# Issue 3: Double spaces
double_space = [s for s in xlsx_skus if '  ' in s['raw_sku']]
if double_space:
    issues.append({
        'type': 'Double spaces in SKU',
        'count': len(double_space),
        'examples': [s['raw_sku'] for s in double_space[:5]]
    })

# Issue 4: Non-numeric variation codes
non_numeric_var = [s for s in xlsx_skus if s['var_code'] and not s['var_code'].isdigit()]
if non_numeric_var:
    issues.append({
        'type': 'Non-numeric variation codes',
        'count': len(non_numeric_var),
        'examples': [f"{s['raw_sku']} -> var={s['var_code']}" for s in non_numeric_var[:5]]
    })

# Issue 5: Folder name mismatches (if we have downloaded folders)
if downloaded_folders:
    xlsx_folder_styles = set(s['folder_style'] for s in xlsx_skus)
    downloaded_set = set(downloaded_folders)
    
    # Folders in Drive but not matching XLSX
    unmatched_drive = downloaded_set - xlsx_folder_styles
    if unmatched_drive:
        issues.append({
            'type': 'Drive folders not matching XLSX',
            'count': len(unmatched_drive),
            'examples': list(unmatched_drive)[:5]
        })

# Print issues
if issues:
    for issue in issues:
        print(f"\n[{issue['type']}] ({issue['count']} occurrences)")
        for ex in issue['examples']:
            print(f"    {ex}")
else:
    print("\nNo major issues found!")

# Save detailed analysis
with open('naming_analysis.txt', 'w', encoding='utf-8') as f:
    f.write("NAMING CONSISTENCY ANALYSIS\n")
    f.write("=" * 80 + "\n\n")
    
    f.write(f"XLSX rows with SKUs: {len(xlsx_skus)}\n")
    f.write(f"Downloaded image folders: {len(downloaded_folders)}\n\n")
    
    f.write("ALL XLSX SKU PATTERNS\n")
    f.write("-" * 80 + "\n")
    f.write(f"{'Row':<6} {'Raw SKU':<35} {'Base':<20} {'Var':<15} {'Folder Style':<30}\n")
    f.write("-" * 106 + "\n")
    for s in xlsx_skus:
        f.write(f"{s['row']:<6} {s['raw_sku']:<35} {s['base_sku'] or 'N/A':<20} {s['var_code'] or 'N/A':<15} {s['folder_style']:<30}\n")

print("\n\nFull analysis saved to naming_analysis.txt")
