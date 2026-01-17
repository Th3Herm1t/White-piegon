from sync_products_v2 import WooCommerceAPI
from config import STORE_URL, CONSUMER_KEY, CONSUMER_SECRET, XLSX_DATA_START_ROW, parse_sku
import pandas as pd
from collections import defaultdict

api = WooCommerceAPI(STORE_URL, CONSUMER_KEY, CONSUMER_SECRET)

def audit_products():
    print("Auditing products from XLSX in WooCommerce...")
    
    # Load XLSX
    df = pd.read_excel('FILLETTE  V3.xlsx', header=None)
    
    # Group by base SKU
    base_skus = set()
    for idx in range(XLSX_DATA_START_ROW, len(df)):
        raw_sku = df.iloc[idx, 2] # SKU column
        if pd.isna(raw_sku): continue
        base, _ = parse_sku(raw_sku)
        if base:
            base_skus.add(base.strip().upper())
            
    print(f"Total Unique Base SKUs in XLSX: {len(base_skus)}")
    
    # Fetch existing products from WooCommerce
    print("Fetching all products from WooCommerce...")
    wc_products = api.get_all_pages('products')
    
    wc_sku_map = {}
    for p in wc_products:
        sku = p.get('sku', '').strip().upper()
        if sku:
            wc_sku_map[sku] = p
            
    # Audit
    found_count = 0
    missing_count = 0
    with_images = 0
    with_variations = 0
    
    audit_results = {
        'found': [],
        'missing': []
    }
    
    for base_sku in sorted(list(base_skus)):
        if base_sku in wc_sku_map:
            found_count += 1
            p = wc_sku_map[base_sku]
            num_images = len(p.get('images', []))
            if num_images > 0: with_images += 1
            
            # Check variations count
            # Note: WC API 'variations' field in product object is just a list of IDs
            num_vars = len(p.get('variations', []))
            if num_vars > 0: with_variations += 1
            
            audit_results['found'].append({
                'sku': base_sku,
                'id': p['id'],
                'images': num_images,
                'variations': num_vars
            })
        else:
            missing_count += 1
            audit_results['missing'].append(base_sku)
            
    print("\n" + "="*50)
    print("AUDIT RESULTS")
    print("="*50)
    print(f"Total SKUs in XLSX:   {len(base_skus)}")
    print(f"Found in WC:          {found_count}")
    print(f"Missing from WC:      {missing_count}")
    print(f"With Images:          {with_images}")
    print(f"With Variations:      {with_variations}")
    
    if audit_results['missing']:
        print("\nTOP 20 MISSING SKUs:")
        for sku in audit_results['missing'][:20]:
            print(f"  - {sku}")
            
    if audit_results['found']:
        print("\nFIRST 10 FOUND SKUs DETAILS:")
        for p in audit_results['found'][:10]:
            print(f"  - {p['sku']}: ID {p['id']}, Images: {p['images']}, Variations: {p['variations']}")

if __name__ == "__main__":
    audit_products()
