"""
WooCommerce Product Sync Script

Syncs products from FILLETTE V3.xlsx to WooCommerce store.
Creates variable products with size variations.

Usage:
    python sync_products.py [--dry-run] [--limit N] [--start-row N]

Options:
    --dry-run       Validate data without creating products
    --limit N       Only process N products
    --start-row N   Start from row N in the XLSX
"""

import os
import sys
import json
import time
import argparse
import pandas as pd
import requests
from requests.auth import HTTPBasicAuth
from datetime import datetime

# Import configuration
from config import (
    STORE_URL, CONSUMER_KEY, CONSUMER_SECRET, API_BASE,
    SIZE_ATTRIBUTE, COLOR_ATTRIBUTE, SIZE_COLUMNS,
    FILLETTE_CATEGORY_ID, get_categories_for_famille,
    XLSX_COLUMNS, XLSX_DATA_START_ROW, XLSX_HEADER_ROW,
    DRY_RUN, SKIP_EXISTING, DEFAULT_STATUS, 
    MANAGE_STOCK, DEFAULT_STOCK_STATUS,
    IMAGE_BASE_URL
)


class WooCommerceAPI:
    """Simple WooCommerce REST API client"""
    
    def __init__(self, store_url, consumer_key, consumer_secret):
        self.base_url = f"{store_url}/wp-json/wc/v3"
        self.auth = HTTPBasicAuth(consumer_key, consumer_secret)
        self.session = requests.Session()
        self.session.auth = self.auth
        
    def get(self, endpoint, params=None):
        """Make a GET request"""
        url = f"{self.base_url}/{endpoint}"
        response = self.session.get(url, params=params or {}, timeout=30)
        response.raise_for_status()
        return response.json()
    
    def post(self, endpoint, data):
        """Make a POST request"""
        url = f"{self.base_url}/{endpoint}"
        response = self.session.post(
            url, 
            json=data, 
            timeout=60,
            headers={'Content-Type': 'application/json'}
        )
        response.raise_for_status()
        return response.json()
    
    def put(self, endpoint, data):
        """Make a PUT request"""
        url = f"{self.base_url}/{endpoint}"
        response = self.session.put(
            url, 
            json=data, 
            timeout=60,
            headers={'Content-Type': 'application/json'}
        )
        response.raise_for_status()
        return response.json()
    
    def get_product_by_sku(self, sku):
        """Check if a product exists by SKU"""
        try:
            products = self.get('products', {'sku': sku})
            return products[0] if products else None
        except:
            return None
    
    def get_all_pages(self, endpoint, per_page=100):
        """Fetch all pages of a paginated endpoint"""
        all_items = []
        page = 1
        while True:
            items = self.get(endpoint, {'per_page': per_page, 'page': page})
            if not items:
                break
            all_items.extend(items)
            if len(items) < per_page:
                break
            page += 1
        return all_items


class ProductSync:
    """Main product sync logic"""
    
    def __init__(self, api, dry_run=False):
        self.api = api
        self.dry_run = dry_run
        self.created_products = []
        self.skipped_products = []
        self.failed_products = []
        self.existing_skus = set()
        
    def load_existing_skus(self):
        """Load all existing product SKUs to avoid duplicates"""
        print("Loading existing product SKUs...")
        products = self.api.get_all_pages('products')
        for p in products:
            if p.get('sku'):
                self.existing_skus.add(p['sku'].strip().upper())
        print(f"Found {len(self.existing_skus)} existing products with SKUs")
        
    def clean_sku(self, raw_sku):
        """Clean and normalize SKU"""
        if pd.isna(raw_sku) or not raw_sku:
            return None
        sku = str(raw_sku).strip()
        # Remove extra spaces
        sku = ' '.join(sku.split())
        return sku
    
    def clean_price(self, raw_price):
        """Clean and normalize price"""
        if pd.isna(raw_price) or raw_price is None:
            return None
        try:
            price = float(raw_price)
            return str(round(price, 2))
        except (ValueError, TypeError):
            return None
    
    def get_available_sizes(self, row):
        """Get list of available sizes from row data"""
        sizes = []
        for col_idx, size_label in SIZE_COLUMNS.items():
            value = row.iloc[col_idx] if col_idx < len(row) else None
            if pd.notna(value) and str(value).strip().upper() == 'X':
                sizes.append(size_label)
        return sizes
    
    def row_to_product(self, row, row_idx):
        """Convert an XLSX row to WooCommerce product data"""
        
        # Extract basic fields
        sku = self.clean_sku(row.iloc[XLSX_COLUMNS['sku']])
        if not sku:
            return None, "No SKU"
        
        name = row.iloc[XLSX_COLUMNS['name']] if pd.notna(row.iloc[XLSX_COLUMNS['name']]) else None
        if not name:
            return None, "No product name"
        
        price = self.clean_price(row.iloc[XLSX_COLUMNS['price']])
        famille = row.iloc[XLSX_COLUMNS['famille']] if pd.notna(row.iloc[XLSX_COLUMNS['famille']]) else None
        color = row.iloc[XLSX_COLUMNS['color']] if pd.notna(row.iloc[XLSX_COLUMNS['color']]) else None
        tech_desc = row.iloc[XLSX_COLUMNS['tech_description']] if pd.notna(row.iloc[XLSX_COLUMNS['tech_description']]) else ''
        description = row.iloc[XLSX_COLUMNS['description']] if pd.notna(row.iloc[XLSX_COLUMNS['description']]) else ''
        
        # Get available sizes
        sizes = self.get_available_sizes(row)
        if not sizes:
            return None, "No sizes available"
        
        # Get categories
        categories = get_categories_for_famille(famille)
        
        # Build product data
        product_data = {
            'name': str(name).strip(),
            'type': 'variable',
            'sku': sku,
            'status': DEFAULT_STATUS,
            'description': str(description).strip() if description else '',
            'short_description': str(tech_desc).strip() if tech_desc else '',
            'categories': [{'id': cat_id} for cat_id in categories],
            'attributes': [
                {
                    'id': SIZE_ATTRIBUTE['id'],
                    'name': SIZE_ATTRIBUTE['name'],
                    'position': 0,
                    'visible': True,
                    'variation': True,
                    'options': sizes
                }
            ]
        }
        
        # Add color attribute if available
        if color:
            product_data['attributes'].append({
                'id': COLOR_ATTRIBUTE['id'],
                'name': COLOR_ATTRIBUTE['name'],
                'position': 1,
                'visible': True,
                'variation': False,
                'options': [str(color).strip()]
            })
        
        # Add images if configured (placeholder for future)
        # if IMAGE_BASE_URL:
        #     product_data['images'] = [{'src': f"{IMAGE_BASE_URL}/{sku}.jpg"}]
        
        return {
            'product_data': product_data,
            'sizes': sizes,
            'price': price,
            'sku': sku
        }, None
    
    def create_variations(self, product_id, sizes, price):
        """Create size variations for a variable product"""
        variations_created = []
        
        for size in sizes:
            variation_data = {
                'regular_price': price if price else '',
                'stock_status': DEFAULT_STOCK_STATUS,
                'attributes': [
                    {
                        'id': SIZE_ATTRIBUTE['id'],
                        'option': size
                    }
                ]
            }
            
            if self.dry_run:
                print(f"      [DRY RUN] Would create variation: {size}")
                variations_created.append({'size': size, 'status': 'dry_run'})
            else:
                try:
                    result = self.api.post(f'products/{product_id}/variations', variation_data)
                    variations_created.append({'size': size, 'id': result['id']})
                    print(f"      Created variation: {size} (ID: {result['id']})")
                except Exception as e:
                    print(f"      ERROR creating variation {size}: {e}")
                    variations_created.append({'size': size, 'error': str(e)})
        
        return variations_created
    
    def sync_product(self, row, row_idx):
        """Sync a single product from XLSX row"""
        
        # Convert row to product data
        result, error = self.row_to_product(row, row_idx)
        if error:
            print(f"  Row {row_idx}: SKIPPED - {error}")
            self.skipped_products.append({'row': row_idx, 'reason': error})
            return False
        
        product_data = result['product_data']
        sizes = result['sizes']
        price = result['price']
        sku = result['sku']
        
        # Check if product exists
        if SKIP_EXISTING and sku.upper() in self.existing_skus:
            print(f"  Row {row_idx}: SKIPPED - SKU '{sku}' already exists")
            self.skipped_products.append({'row': row_idx, 'sku': sku, 'reason': 'exists'})
            return False
        
        print(f"  Row {row_idx}: Processing '{product_data['name'][:50]}...' (SKU: {sku})")
        print(f"      Sizes: {', '.join(sizes)}")
        print(f"      Price: {price}")
        
        if self.dry_run:
            print(f"      [DRY RUN] Would create product with {len(sizes)} variations")
            self.created_products.append({
                'row': row_idx,
                'sku': sku,
                'name': product_data['name'],
                'status': 'dry_run'
            })
            return True
        
        try:
            # Create the variable product
            created_product = self.api.post('products', product_data)
            product_id = created_product['id']
            print(f"      Created product ID: {product_id}")
            
            # Create variations
            variations = self.create_variations(product_id, sizes, price)
            
            self.created_products.append({
                'row': row_idx,
                'sku': sku,
                'name': product_data['name'],
                'id': product_id,
                'variations': len(variations)
            })
            
            # Small delay to avoid rate limiting
            time.sleep(0.5)
            
            return True
            
        except Exception as e:
            print(f"      ERROR: {e}")
            self.failed_products.append({
                'row': row_idx,
                'sku': sku,
                'error': str(e)
            })
            return False
    
    def sync_from_xlsx(self, xlsx_path, limit=None, start_row=None):
        """Main sync function"""
        
        print("=" * 80)
        print(f"WooCommerce Product Sync - {'DRY RUN' if self.dry_run else 'LIVE'}")
        print("=" * 80)
        print(f"XLSX file: {xlsx_path}")
        print(f"Store: {STORE_URL}")
        print(f"Limit: {limit if limit else 'No limit'}")
        print(f"Start row: {start_row if start_row else 'From beginning'}")
        print("=" * 80)
        
        # Load existing SKUs
        if SKIP_EXISTING and not self.dry_run:
            self.load_existing_skus()
        
        # Read XLSX
        print(f"\nReading XLSX file...")
        df = pd.read_excel(xlsx_path, header=None)
        print(f"Total rows in file: {len(df)}")
        
        # Determine row range
        data_start = start_row if start_row else XLSX_DATA_START_ROW
        data_end = len(df)
        
        if limit:
            data_end = min(data_start + limit, len(df))
        
        print(f"Processing rows {data_start} to {data_end - 1}")
        print("=" * 80)
        
        # Process each row
        for idx in range(data_start, data_end):
            row = df.iloc[idx]
            
            # Skip empty rows (check if famille and sku are both empty)
            famille = row.iloc[XLSX_COLUMNS['famille']] if XLSX_COLUMNS['famille'] < len(row) else None
            sku = row.iloc[XLSX_COLUMNS['sku']] if XLSX_COLUMNS['sku'] < len(row) else None
            
            if pd.isna(famille) and pd.isna(sku):
                continue
            
            self.sync_product(row, idx)
        
        # Print summary
        self.print_summary()
        
        # Save log
        self.save_log()
    
    def print_summary(self):
        """Print sync summary"""
        print("\n" + "=" * 80)
        print("SYNC SUMMARY")
        print("=" * 80)
        print(f"Created: {len(self.created_products)}")
        print(f"Skipped: {len(self.skipped_products)}")
        print(f"Failed:  {len(self.failed_products)}")
        
        if self.failed_products:
            print("\nFailed products:")
            for p in self.failed_products:
                print(f"  Row {p['row']}: {p.get('sku', 'N/A')} - {p['error']}")
    
    def save_log(self):
        """Save sync log to JSON file"""
        log_file = f"sync_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        log_data = {
            'timestamp': datetime.now().isoformat(),
            'dry_run': self.dry_run,
            'created': self.created_products,
            'skipped': self.skipped_products,
            'failed': self.failed_products
        }
        
        with open(log_file, 'w', encoding='utf-8') as f:
            json.dump(log_data, f, indent=2, ensure_ascii=False)
        
        print(f"\nLog saved to: {log_file}")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Sync products from XLSX to WooCommerce')
    parser.add_argument('--dry-run', action='store_true', help='Validate without creating products')
    parser.add_argument('--limit', type=int, help='Limit number of products to process')
    parser.add_argument('--start-row', type=int, help='Start from specific row number')
    parser.add_argument('--xlsx', type=str, default='FILLETTE  V3.xlsx', help='Path to XLSX file')
    
    args = parser.parse_args()
    
    # Validate configuration
    if not STORE_URL or not CONSUMER_KEY or not CONSUMER_SECRET:
        print("ERROR: Missing WooCommerce credentials in .env file")
        print("Required: STORE_URL, Key, SECRET")
        sys.exit(1)
    
    # Check XLSX file exists
    xlsx_path = args.xlsx
    if not os.path.exists(xlsx_path):
        print(f"ERROR: XLSX file not found: {xlsx_path}")
        sys.exit(1)
    
    # Initialize API client
    api = WooCommerceAPI(STORE_URL, CONSUMER_KEY, CONSUMER_SECRET)
    
    # Test API connection
    print("Testing API connection...")
    try:
        api.get('products', {'per_page': 1})
        print("API connection successful!")
    except Exception as e:
        print(f"ERROR: API connection failed: {e}")
        sys.exit(1)
    
    # Run sync
    syncer = ProductSync(api, dry_run=args.dry_run or DRY_RUN)
    syncer.sync_from_xlsx(xlsx_path, limit=args.limit, start_row=args.start_row)


if __name__ == '__main__':
    main()
