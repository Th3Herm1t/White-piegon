from sync_products_v2 import WooCommerceAPI
from config import STORE_URL, CONSUMER_KEY, CONSUMER_SECRET, FILLETTE_CATEGORY_ID
import json

api = WooCommerceAPI(STORE_URL, CONSUMER_KEY, CONSUMER_SECRET)

def check_fillette_products():
    print(f"Checking products in category ID {FILLETTE_CATEGORY_ID} (Fillette)...")
    
    # Fetch products in Fillette category
    products = api.get_all_pages('products', per_page=100)
    
    fillette_products = []
    for p in products:
        cat_ids = [c['id'] for c in p.get('categories', [])]
        if FILLETTE_CATEGORY_ID in cat_ids:
            fillette_products.append(p)
            
    print(f"Total products found in 'Fillette' category: {len(fillette_products)}")
    
    # Sort by date created (descending) to see recent ones
    fillette_products.sort(key=lambda x: x['date_created'], reverse=True)
    
    print("\nRECENT 30 PRODUCTS IN FILLETTE:")
    for p in fillette_products[:30]:
        sku = p.get('sku', 'NO SKU')
        num_vars = len(p.get('variations', []))
        num_imgs = len(p.get('images', []))
        print(f"  - [{p['date_created']}] ID: {p['id']}, SKU: {sku:<15}, Name: {p['name'][:30]:<30}, Vars: {num_vars}, Imgs: {num_imgs}")

if __name__ == "__main__":
    check_fillette_products()
