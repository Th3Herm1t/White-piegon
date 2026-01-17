"""
Validate Price vs Image Availability Correlation

Checks the user's hypothesis: "If the price field is not empty then the image is available"
"""

import pandas as pd
from config import XLSX_COLUMNS, XLSX_DATA_START_ROW
from image_mapping import normalize_sku, scan_image_folders, find_images_for_sku

# Read XLSX
df = pd.read_excel('FILLETTE  V3.xlsx', header=None)

# Scan image folders
folder_map = scan_image_folders()

# Counters
total_rows = 0
price_present_count = 0
price_missing_count = 0

price_present_image_found = 0
price_present_image_missing = 0

price_missing_image_found = 0
price_missing_image_missing = 0

# List for detailed report
details = []

for i in range(XLSX_DATA_START_ROW, len(df)):
    raw_sku = df.iloc[i, XLSX_COLUMNS['sku']]
    raw_price = df.iloc[i, XLSX_COLUMNS['price']]
    
    if pd.isna(raw_sku):
        continue
    
    total_rows += 1
    
    # Check Price
    has_price = pd.notna(raw_price) and str(raw_price).strip() != ''
    
    # Check Image
    images = find_images_for_sku(raw_sku, folder_map)
    has_image = len(images) > 0
    
    if has_price:
        price_present_count += 1
        if has_image:
            price_present_image_found += 1
        else:
            price_present_image_missing += 1
            details.append({
                'row': i,
                'sku': raw_sku,
                'price': raw_price,
                'status': 'HAS PRICE but NO IMAGE'
            })
    else:
        price_missing_count += 1
        if has_image:
            price_missing_image_found += 1
            details.append({
                'row': i,
                'sku': raw_sku,
                'price': 'MISSING',
                'status': 'NO PRICE but HAS IMAGE'
            })
        else:
            price_missing_image_missing += 1

# Report
print("=" * 80)
print("PRICE VS IMAGE CORRELATION REPORT")
print("=" * 80)

print(f"Total Rows with SKUs: {total_rows}")
print(f"Rows with PRICE: {price_present_count}")
print(f"Rows without PRICE: {price_missing_count}")

print("\n--- HYPOTHESIS CHECK ---")
print(f"Hypothesis: 'Price Not Empty -> Image Available'")

print(f"\n1. Rows WITH Price ({price_present_count}):")
print(f"   - Found Image: {price_present_image_found} ({price_present_image_found/price_present_count*100:.1f}%)")
print(f"   - Missing Image: {price_present_image_missing} ({price_present_image_missing/price_present_count*100:.1f}%)")

print(f"\n2. Rows WITHOUT Price ({price_missing_count}):")
print(f"   - Found Image: {price_missing_image_found}")
print(f"   - Missing Image: {price_missing_image_missing}")

print("\n" + "=" * 80)
print("EXCEPTIONS (First 20)")
print("=" * 80)

if details:
    for d in details[:20]:
        print(f"Row {d['row']}: {d['sku']:<30} Price: {d['price']:<10} -> {d['status']}")
else:
    print("No exceptions found! The rule holds perfectly.")
