from sync_products_v2 import WooCommerceAPI
from config import STORE_URL, CONSUMER_KEY, CONSUMER_SECRET

api = WooCommerceAPI(STORE_URL, CONSUMER_KEY, CONSUMER_SECRET)

def verify_product(product_id):
    print(f"\nVerifying Product ID: {product_id}")
    try:
        p = api.get(f'products/{product_id}')
        print(f"Name: {p['name']}")
        print(f"SKU: {p['sku']}")
        print(f"Type: {p['type']}")
        print(f"Images: {len(p['images'])}")
        for img in p['images']:
            print(f"  - Image ID: {img['id']}, Src: {img['src']}")
            
        vars = api.get(f'products/{product_id}/variations')
        print(f"Variations: {len(vars)}")
        if vars:
            v = vars[0]
            print(f"Sample Variation SKU: {v['sku']}")
            print(f"Sample Variation Image ID: {v.get('image', {}).get('id') if v.get('image') else 'None'}")
            print(f"Sample Variation Attributes: {v['attributes']}")
    except Exception as e:
        print(f"Error: {e}")

# Verify some representative products
verify_product(38154) # SWEAT MOLLETON (Rose Fuchsia) - with images
verify_product(38180) # SWEAT COL ROND (Multi-color) - with no images
verify_product(38249) # CALÇON - simple variation
