"""Check recently created products"""
import json
import requests
from requests.auth import HTTPBasicAuth
from config import API_BASE, CONSUMER_KEY, CONSUMER_SECRET

# Get 10 most recent products
r = requests.get(
    f'{API_BASE}/products', 
    auth=HTTPBasicAuth(CONSUMER_KEY, CONSUMER_SECRET), 
    params={'per_page': 10, 'orderby': 'id', 'order': 'desc'}
)
products = r.json()

with open('recent_products.txt', 'w', encoding='utf-8') as f:
    f.write("=" * 80 + "\n")
    f.write("RECENTLY CREATED PRODUCTS\n")
    f.write("=" * 80 + "\n")
    
    for p in products:
        f.write(f"\n[{p['id']}] {p['name']}\n")
        f.write(f"    SKU: {p.get('sku', 'N/A')}\n")
        f.write(f"    Type: {p['type']}\n")
        f.write(f"    Price: {p.get('price', 'N/A')}\n")
        f.write(f"    Status: {p.get('status', 'N/A')}\n")
        f.write(f"    Variations: {len(p.get('variations', []))}\n")
        
        # Show categories
        cats = [c['name'] for c in p.get('categories', [])]
        f.write(f"    Categories: {', '.join(cats)}\n")
        
        # Show attributes
        for attr in p.get('attributes', []):
            opts = ', '.join(attr.get('options', []))
            f.write(f"    Attribute '{attr['name']}': {opts}\n")

print("Output saved to recent_products.txt")
