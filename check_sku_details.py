from sync_products_v2 import WooCommerceAPI
from config import STORE_URL, CONSUMER_KEY, CONSUMER_SECRET

api = WooCommerceAPI(STORE_URL, CONSUMER_KEY, CONSUMER_SECRET)

def check_sku(sku):
    print(f"Checking SKU: {sku}")
    p = api.get_product_by_sku(sku)
    if p:
        print(f"Found as Product: ID {p['id']}, Type: {p['type']}")
        if p['type'] == 'variable':
            vars = api.get(f"products/{p['id']}/variations")
            print(f"Variations for {sku}:")
            for v in vars:
                print(f"  - Variation ID: {v['id']}, SKU: {v['sku']}")
    else:
        print("Not found via direct SKU search.")
        
check_sku('WPMF001')
check_sku('WPMF001 ROSE')
check_sku('WPMF 001 ROSE')
