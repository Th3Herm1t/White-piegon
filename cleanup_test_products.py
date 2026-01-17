"""
Cleanup Script

Deletes test products created during development.
"""

import argparse
from config import STORE_URL, CONSUMER_KEY, CONSUMER_SECRET, API_BASE
from sync_products_v2 import WooCommerceAPI

# IDs of products to delete
# 36900: WPJF 001 -120 (V1)
# 36909: WPJF 001-127 (V1)
# 36918: WPJF 002 -130 (V1)
# 36927: WPJF 008 (V2 test - optional to delete)

IDS_TO_DELETE = [36900, 36909, 36918]

def main():
    parser = argparse.ArgumentParser(description='Delete test products')
    parser.add_argument('--include-v2', action='store_true', help='Also delete V2 test product (36927)')
    args = parser.parse_args()
    
    ids = list(IDS_TO_DELETE)
    if args.include_v2:
        ids.append(36927)
        
    print(f"Deleting {len(ids)} products: {ids}")
    
    api = WooCommerceAPI(STORE_URL, CONSUMER_KEY, CONSUMER_SECRET)
    
    for pid in ids:
        try:
            print(f"Deleting product {pid}...")
            # force=True to bypass trash
            api.session.delete(f"{API_BASE}/products/{pid}", params={'force': True})
            print(f"  Deleted {pid}")
        except Exception as e:
            print(f"  Error deleting {pid}: {e}")

if __name__ == '__main__':
    main()
