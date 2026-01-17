"""
WooCommerce Store Explorer

This script connects to the WooCommerce store and fetches:
1. Existing products  
2. Product categories
3. Product attributes
4. Product tags
"""

import os
import json
import requests
from requests.auth import HTTPBasicAuth

# Get credentials from .env
with open('.env', 'r') as f:
    env_content = f.read()
    
# Parse .env
env_vars = {}
for line in env_content.strip().split('\n'):
    if '=' in line:
        key, value = line.strip().split('=', 1)
        env_vars[key] = value

consumer_key = env_vars.get('Key', env_vars.get('KEY', ''))
consumer_secret = env_vars.get('SECRET', env_vars.get('Secret', ''))

print(f"Consumer Key: {consumer_key[:20]}...")
print(f"Consumer Secret: {consumer_secret[:20]}...")

# You need to provide the store URL
# Let's try to find it or ask the user
STORE_URL = None

# Check if STORE_URL is in .env
if 'STORE_URL' in env_vars:
    STORE_URL = env_vars['STORE_URL']
elif 'URL' in env_vars:
    STORE_URL = env_vars['URL']

if not STORE_URL:
    print("\n" + "="*80)
    print("ERROR: Store URL not found in .env file!")
    print("Please add STORE_URL=https://yourstore.com to your .env file")
    print("="*80)
    exit(1)

# Remove trailing slash
STORE_URL = STORE_URL.rstrip('/')

print(f"\nStore URL: {STORE_URL}")

# API Base URL
API_BASE = f"{STORE_URL}/wp-json/wc/v3"

def make_request(endpoint, params=None):
    """Make an authenticated request to WooCommerce API"""
    url = f"{API_BASE}/{endpoint}"
    try:
        response = requests.get(
            url,
            auth=HTTPBasicAuth(consumer_key, consumer_secret),
            params=params or {},
            timeout=30
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching {endpoint}: {e}")
        return None

def fetch_all_pages(endpoint, per_page=100):
    """Fetch all pages of a paginated endpoint"""
    all_items = []
    page = 1
    while True:
        items = make_request(endpoint, {'per_page': per_page, 'page': page})
        if not items:
            break
        all_items.extend(items)
        if len(items) < per_page:
            break
        page += 1
    return all_items

print("\n" + "="*80)
print("FETCHING STORE DATA...")
print("="*80)

# 1. Fetch products
print("\n1. Fetching products...")
products = fetch_all_pages('products')
print(f"   Found {len(products)} products")

# 2. Fetch categories
print("\n2. Fetching product categories...")
categories = fetch_all_pages('products/categories')
print(f"   Found {len(categories)} categories")

# 3. Fetch attributes
print("\n3. Fetching product attributes...")
attributes = fetch_all_pages('products/attributes')
print(f"   Found {len(attributes)} attributes")

# 4. Fetch tags
print("\n4. Fetching product tags...")
tags = fetch_all_pages('products/tags')
print(f"   Found {len(tags)} tags")

# Save to JSON files for analysis
output = {
    'products': products,
    'categories': categories, 
    'attributes': attributes,
    'tags': tags
}

with open('woocommerce_data.json', 'w', encoding='utf-8') as f:
    json.dump(output, f, indent=2, ensure_ascii=False)
print("\n\nData saved to woocommerce_data.json")

# Print summary
print("\n" + "="*80)
print("SUMMARY")
print("="*80)

print("\n--- CATEGORIES ---")
for cat in categories:
    parent_info = f" (parent: {cat.get('parent')})" if cat.get('parent') else ""
    print(f"  [{cat['id']}] {cat['name']}{parent_info} - {cat.get('count', 0)} products")

print("\n--- ATTRIBUTES ---")
for attr in attributes:
    print(f"  [{attr['id']}] {attr['name']} (slug: {attr['slug']})")

print("\n--- PRODUCTS (first 20) ---")
for prod in products[:20]:
    cats = ', '.join([c['name'] for c in prod.get('categories', [])])
    print(f"  [{prod['id']}] {prod['name'][:50]} - SKU: {prod.get('sku', 'N/A')} - Price: {prod.get('price', 'N/A')} - Categories: {cats}")

print(f"\n   ... and {len(products) - 20} more products" if len(products) > 20 else "")
