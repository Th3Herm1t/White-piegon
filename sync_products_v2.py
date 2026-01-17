"""
WooCommerce Product Sync Script - v2

Syncs products from FILLETTE V3.xlsx to WooCommerce store.
Groups rows by base SKU and creates variable products with SIZE x COLOR variations.

Usage:
    python sync_products_v2.py [--dry-run] [--limit N] [--start-row N]

Options:
    --dry-run       Validate data without creating products
    --limit N       Only process N base products
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
from collections import defaultdict

# Import configuration
from config import (
    STORE_URL, CONSUMER_KEY, CONSUMER_SECRET, API_BASE,
    SIZE_ATTRIBUTE, COLOR_ATTRIBUTE, SIZE_COLUMNS,
    FILLETTE_CATEGORY_ID, get_categories_for_famille,
    XLSX_COLUMNS, XLSX_DATA_START_ROW, XLSX_HEADER_ROW,
    DRY_RUN, SKIP_EXISTING, DEFAULT_STATUS, 
    MANAGE_STOCK, DEFAULT_STOCK_STATUS,
    parse_sku, get_base_sku
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
        try:
            response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            try:
                error_msg = response.json()
                print(f"      API ERROR: {error_msg.get('message', str(e))}")
            except:
                print(f"      API ERROR: {e}")
            raise
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
        try:
            response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            try:
                error_msg = response.json()
                print(f"      API ERROR: {error_msg.get('message', str(e))}")
            except:
                print(f"      API ERROR: {e}")
            raise
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


class ProductSyncV2:
    """Product sync with COLOR x SIZE variation support"""
    
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
                # Store both original and base SKU
                sku = p['sku'].strip()
                self.existing_skus.add(sku.upper())
                base = get_base_sku(sku)
                if base:
                    self.existing_skus.add(base.upper())
        print(f"Found {len(self.existing_skus)} existing SKUs")
    
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
    
    def group_rows_by_base_sku(self, df, start_row, end_row):
        """Group XLSX rows by base SKU"""
        groups = defaultdict(list)
        
        for idx in range(start_row, end_row):
            row = df.iloc[idx]
            raw_sku = row.iloc[XLSX_COLUMNS['sku']]
            
            if pd.isna(raw_sku):
                continue
            
            base_sku, var_code = parse_sku(raw_sku)
            if not base_sku:
                continue
            
            groups[base_sku].append({
                'row_idx': idx,
                'row': row,
                'raw_sku': str(raw_sku).strip(),
                'var_code': var_code,
                'color': row.iloc[XLSX_COLUMNS['color']] if pd.notna(row.iloc[XLSX_COLUMNS['color']]) else var_code,
                'sizes': self.get_available_sizes(row),
                'price': self.clean_price(row.iloc[XLSX_COLUMNS['price']]),
                'name': row.iloc[XLSX_COLUMNS['name']] if pd.notna(row.iloc[XLSX_COLUMNS['name']]) else None,
                'famille': row.iloc[XLSX_COLUMNS['famille']] if pd.notna(row.iloc[XLSX_COLUMNS['famille']]) else None,
                'tech_desc': row.iloc[XLSX_COLUMNS['tech_description']] if pd.notna(row.iloc[XLSX_COLUMNS['tech_description']]) else '',
                'description': row.iloc[XLSX_COLUMNS['description']] if pd.notna(row.iloc[XLSX_COLUMNS['description']]) else '',
            })
        
        return groups
    
    def create_product_from_group(self, base_sku, variants, folder_map):
        """Create or update a variable product from grouped variants"""
        
        # Check if product exists - get the actual product object
        existing_product = self.api.get_product_by_sku(base_sku)
        
        # If it doesn't exist by base SKU, check if it exists by one of its variation SKUs 
        # (common in messy imports)
        if not existing_product and variants:
            for v in variants:
                existing_product = self.api.get_product_by_sku(v['raw_sku'])
                if existing_product:
                    # If it's a simple product but we want it variable, we'll keep it or update it
                    break
        
        if existing_product and SKIP_EXISTING:
            # Check if it's already "complete" (has variations and images)
            num_vars = len(existing_product.get('variations', []))
            num_imgs = len(existing_product.get('images', []))
            if num_vars > 0 and num_imgs > 0:
                print(f"  SKIPPED - Base SKU '{base_sku}' is already complete (ID: {existing_product['id']})")
                self.skipped_products.append({'sku': base_sku, 'reason': 'complete'})
                return False
            else:
                print(f"  EXISTING BUT INCOMPLETE - Updating Base SKU '{base_sku}' (ID: {existing_product['id']})")
        elif existing_product:
            print(f"  UPDATING - Base SKU '{base_sku}' (ID: {existing_product['id']})")
        else:
            print(f"  NEW - Creating Base SKU '{base_sku}'")
            
        # Use first variant for base product info
        first_variant = variants[0]
        
        # Get product name from first variant with a name
        product_name = None
        for v in variants:
            if v['name']:
                product_name = str(v['name']).strip()
                break
        
        if not product_name and existing_product:
            product_name = existing_product['name']
            
        if not product_name:
            print(f"  SKIPPED - No product name for '{base_sku}'")
            self.skipped_products.append({'sku': base_sku, 'reason': 'no_name'})
            return False
            
        # Collect all colors, sizes, and images across variants
        all_colors = []
        all_sizes = set()
        best_price = None
        
        from image_mapping import find_images_for_sku
        
        # Collect images for the main product
        product_images = []
        seen_images = set()

        for v in variants:
            color = v['color']
            if color and str(color).strip():
                color_clean = str(color).strip()
                if color_clean not in all_colors:
                    all_colors.append(color_clean)
            all_sizes.update(v['sizes'])
            if v['price'] and (best_price is None or float(v['price']) < float(best_price)):
                best_price = v['price']
            
            # Find images for this variant
            imgs = find_images_for_sku(v['raw_sku'], folder_map)
            v['images'] = imgs # Store for variation image logic
            
            # Add to main product images
            for img_path in imgs:
                img_name = os.path.basename(img_path)
                if img_name not in seen_images:
                    product_images.append(img_path)
                    seen_images.add(img_name)
        
        all_sizes = sorted(list(all_sizes), key=lambda x: (len(x), x))
        
        if not all_sizes:
            print(f"  SKIPPED - No sizes for '{base_sku}'")
            self.skipped_products.append({'sku': base_sku, 'reason': 'no_sizes'})
            return False
        
        # Get categories
        categories = get_categories_for_famille(first_variant['famille'])
        
        print(f"\n  Creating: {product_name[:50]}... (SKU: {base_sku})")
        print(f"      Colors: {', '.join(all_colors) if all_colors else 'None'}")
        print(f"      Sizes: {', '.join(all_sizes)}")
        print(f"      Price: {best_price}")
        print(f"      Images: {len(product_images)}")
        print(f"      Variants in XLSX: {len(variants)}")
        
        # Prepare valid image list for API (requires Uploading first or URL)
        # Since we have local files, we need to upload them to WP first or use a plugin
        # BUT the standard WP API requires image URLs (public) or IDs
        # To upload local images, we need to use the /media endpoint
        
        # For this implementation, let's assume we upload them and get IDs
        uploaded_images = []
        if not self.dry_run and product_images:
            print(f"      Uploading {len(product_images)} images...")
            for img_path in product_images:
                wp_image = self.upload_image(img_path)
                if wp_image:
                    uploaded_images.append({'id': wp_image['id']})
        
        # Build product data
        product_data = {
            'name': product_name,
            'type': 'variable',
            'sku': base_sku,
            'status': DEFAULT_STATUS,
            'description': str(first_variant['description']).strip() if first_variant['description'] else '',
            'short_description': str(first_variant['tech_desc']).strip() if first_variant['tech_desc'] else '',
            'categories': [{'id': cat_id} for cat_id in categories],
            'attributes': [],
            'images': uploaded_images
        }
        
        # Add Size attribute (always)
        product_data['attributes'].append({
            'id': SIZE_ATTRIBUTE['id'],
            'name': SIZE_ATTRIBUTE['name'],
            'position': 0,
            'visible': True,
            'variation': True,
            'options': all_sizes
        })
        
        # Add Color attribute if there are colors
        if all_colors:
            product_data['attributes'].append({
                'id': COLOR_ATTRIBUTE['id'],
                'name': COLOR_ATTRIBUTE['name'],
                'position': 1,
                'visible': True,
                'variation': True,
                'options': all_colors
            })
        
        if self.dry_run:
            print(f"      [DRY RUN] Would create product with {len(all_sizes)} sizes x {len(all_colors) or 1} colors")
            self.created_products.append({
                'sku': base_sku,
                'name': product_name,
                'sizes': len(all_sizes),
                'colors': len(all_colors),
                'status': 'dry_run'
            })
            return True
        
        try:
            if existing_product:
                # Update existing product
                product_id = existing_product['id']
                created_product = self.api.put(f"products/{product_id}", product_data)
                print(f"      Updated product ID: {product_id}")
            else:
                # Create the variable product
                created_product = self.api.post('products', product_data)
                product_id = created_product['id']
                print(f"      Created product ID: {product_id}")
            
            # Create/Update variations for each COLOR x SIZE combination
            variations_created = self.create_variations(product_id, variants, all_sizes, all_colors, best_price)
            
            self.created_products.append({
                'sku': base_sku,
                'name': product_name,
                'id': product_id,
                'variations': variations_created
            })
            
            # Small delay to avoid rate limiting
            time.sleep(0.5)
            
            return True
            
        except Exception as e:
            print(f"      ERROR: {e}")
            self.failed_products.append({
                'sku': base_sku,
                'error': str(e)
            })
            return False
    
    def upload_image(self, image_path):
        """Upload an image to WordPress Media Library"""
        if not os.path.exists(image_path):
            return None
            
        filename = os.path.basename(image_path)
        mime_type = 'image/jpeg'
        if filename.lower().endswith('.png'):
            mime_type = 'image/png'
        elif filename.lower().endswith('.webp'):
            mime_type = 'image/webp'
            
        from config import WP_USERNAME, WP_APP_PASSWORD
        
        try:
            # Prepare headers for media upload
            headers = {
                'Content-Disposition': f'attachment; filename="{filename}"',
                'Content-Type': mime_type
            }
            
            # Use WordPress Application Password for authentication if available
            # otherwise fall back to WooCommerce credentials (which usually fails for media)
            auth = self.api.auth
            if WP_USERNAME and WP_APP_PASSWORD:
                auth = HTTPBasicAuth(WP_USERNAME, WP_APP_PASSWORD)
            
            with open(image_path, 'rb') as img_file:
                # Use WP API for media (wp/v2/media) not WC API
                url = f"{self.api.base_url.replace('/wc/v3', '/wp/v2')}/media"
                
                response = self.api.session.post(
                    url,
                    data=img_file,
                    headers=headers,
                    auth=auth,
                    timeout=60
                )
                
                if response.status_code == 401:
                    print(f"      ERROR: Unauthorized upload (401). Please ensure WP_USERNAME and WP_APP_PASSWORD are correct in .env")
                    return None
                    
                response.raise_for_status()
                return response.json()
        except Exception as e:
            print(f"      ERROR uploading image {filename}: {e}")
            return None

    def create_variations(self, product_id, variants, all_sizes, all_colors, default_price):
        """Create or update SIZE x COLOR variations"""
        variations_created = 0
        variations_updated = 0
        
        # Fetch existing variations to avoid duplicates
        print(f"      Fetching existing variations for product {product_id}...")
        existing_vars = self.api.get(f'products/{product_id}/variations', {'per_page': 100})
        
        # Map existing variations by their attribute combination
        # key: (size_option, color_option)
        existing_var_map = {}
        for ev in existing_vars:
            size_opt = None
            color_opt = None
            for attr in ev.get('attributes', []):
                if attr.get('id') == SIZE_ATTRIBUTE['id']:
                    size_opt = attr.get('option')
                elif attr.get('id') == COLOR_ATTRIBUTE['id']:
                    color_opt = attr.get('option')
            existing_var_map[(size_opt, color_opt)] = ev
            
        # Build a map of color -> sizes, price, and image ID from XLSX
        color_data = {}
        
        # Upload variation images first
        for v in variants:
            color = str(v['color']).strip() if v['color'] else 'Default'
            
            # Find image for this variant
            image_id = None
            if not self.dry_run and v.get('images'):
                # Use the first image found for this variant
                img_path = v['images'][0]
                img_name = os.path.basename(img_path)
                
                # Optimization: check if we already uploaded an image with this name today?
                # For now, just upload
                print(f"      Uploading variation image {img_name} for color {color}...")
                wp_img = self.upload_image(img_path)
                if wp_img:
                    image_id = wp_img['id']
            
            if color not in color_data:
                color_data[color] = {
                    'sizes': set(),
                    'price': v['price'],
                    'image_id': image_id
                }
            color_data[color]['sizes'].update(v['sizes'])
            if v['price'] and not color_data[color]['price']:
                color_data[color]['price'] = v['price']
            if image_id and not color_data[color]['image_id']:
                color_data[color]['image_id'] = image_id
        
        # If no colors in XLSX, just handle size variations
        effective_colors = all_colors if all_colors else [None]
        
        for color in effective_colors:
            cd = color_data.get(color, {'sizes': all_sizes, 'price': default_price, 'image_id': None})
            color_sizes = cd['sizes'] if cd['sizes'] else all_sizes
            color_price = cd['price'] if cd['price'] else default_price
            color_image = cd.get('image_id')
            
            for size in color_sizes:
                try:
                    variation_data = {
                        'regular_price': color_price if color_price else '',
                        'stock_status': DEFAULT_STOCK_STATUS,
                        'attributes': [
                            {'id': SIZE_ATTRIBUTE['id'], 'option': size}
                        ]
                    }
                    if color:
                        variation_data['attributes'].append({'id': COLOR_ATTRIBUTE['id'], 'option': color})
                    
                    if color_image:
                        variation_data['image'] = {'id': color_image}
                    
                    # Check if this size/color combination exists
                    key = (size, color)
                    if key in existing_var_map:
                        ev = existing_var_map[key]
                        # Update? For now only if price/image is missing or we want to force it
                        # Let's update to ensure latest data
                        self.api.put(f'products/{product_id}/variations/{ev["id"]}', variation_data)
                        variations_updated += 1
                    else:
                        # Create new
                        self.api.post(f'products/{product_id}/variations', variation_data)
                        variations_created += 1
                except Exception as e:
                    print(f"        ERROR syncing variation {color}/{size}: {e}")
        
        print(f"      Created {variations_created}, Updated {variations_updated} variations")
        return variations_created + variations_updated
    
    def sync_from_xlsx(self, xlsx_path, limit=None, start_row=None):
        """Main sync function"""
        
        print("=" * 80)
        print(f"WooCommerce Product Sync v2 - {'DRY RUN' if self.dry_run else 'LIVE'}")
        print("=" * 80)
        print(f"XLSX file: {xlsx_path}")
        print(f"Store: {STORE_URL}")
        print(f"Mode: Groups rows by base SKU, creates SIZE x COLOR variations")
        print("=" * 80)

        # Load existing SKUs first
        if SKIP_EXISTING and not self.dry_run:
            self.load_existing_skus()
        
        # Load image mapping once
        print("Scanning image folders...")
        from image_mapping import scan_image_folders
        folder_map = scan_image_folders()
        print(f"Found {len(folder_map)} image folders")
        
        # Load XLSX
        print(f"Loading {xlsx_path}...")
        try:
            df = pd.read_excel(xlsx_path, header=None)
        except Exception as e:
            print(f"Error loading Excel file: {e}")
            return
            
        # Determine row range
        data_start = start_row if start_row is not None else XLSX_DATA_START_ROW
        print(f"Processing rows starting from {data_start}")

        # Group rows by base SKU
        groups = self.group_rows_by_base_sku(df, data_start, len(df))
        print(f"Found {len(groups)} unique base SKUs")
        
        # Process groups
        processed = 0
        success = 0
        
        for base_sku, variants in groups.items():
            if limit and processed >= limit:
                print(f"Limit of {limit} reached.")
                break
                
            processed += 1
            if self.create_product_from_group(base_sku, variants, folder_map):
                success += 1
                
        print("\n" + "="*50)
        print("SYNC COMPLETE")
        print(f"Processed: {processed}")
        print(f"Created/Updated: {success}")
        print(f"Skipped: {len(self.skipped_products)}")
        print(f"Failed:  {len(self.failed_products)}")
        
        if self.failed_products:
            print("\nFailed products:")
            for p in self.failed_products:
                print(f"  {p.get('sku', 'N/A')} - {p['error']}")

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
                print(f"  {p.get('sku', 'N/A')} - {p['error']}")
    
    def save_log(self):
        """Save sync log to JSON file"""
        log_file = f"sync_v2_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
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
    parser = argparse.ArgumentParser(description='Sync products from XLSX to WooCommerce (v2 with color variations)')
    parser.add_argument('--dry-run', action='store_true', help='Validate without creating products')
    parser.add_argument('--limit', type=int, help='Limit number of base products to process')
    parser.add_argument('--start-row', type=int, help='Start from specific row number')
    parser.add_argument('--xlsx', type=str, default='FILLETTE  V3.xlsx', help='Path to XLSX file')
    
    args = parser.parse_args()
    
    # Validate configuration
    if not STORE_URL or not CONSUMER_KEY or not CONSUMER_SECRET:
        print("ERROR: Missing WooCommerce credentials in .env file")
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
    syncer = ProductSyncV2(api, dry_run=args.dry_run or DRY_RUN)
    syncer.sync_from_xlsx(xlsx_path, limit=args.limit, start_row=args.start_row)


if __name__ == '__main__':
    main()
