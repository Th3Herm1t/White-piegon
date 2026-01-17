import json

data = json.load(open('woocommerce_data.json', encoding='utf-8'))

with open('analysis_output.txt', 'w', encoding='utf-8') as f:
    f.write("=" * 80 + "\n")
    f.write("WOOCOMMERCE STORE DATA SUMMARY\n")
    f.write("=" * 80 + "\n")
    f.write(f"\nProducts: {len(data['products'])}\n")
    f.write(f"Categories: {len(data['categories'])}\n")
    f.write(f"Attributes: {len(data['attributes'])}\n")
    f.write(f"Tags: {len(data['tags'])}\n")

    f.write("\n" + "=" * 80 + "\n")
    f.write("CATEGORIES\n")
    f.write("=" * 80 + "\n")
    for c in data['categories']:
        parent_info = f" (parent: {c.get('parent')})" if c.get('parent') else ""
        f.write(f"  [{c['id']}] {c['name']} - {c.get('count', 0)} products{parent_info}\n")

    f.write("\n" + "=" * 80 + "\n")
    f.write("ATTRIBUTES\n")
    f.write("=" * 80 + "\n")
    for a in data['attributes']:
        f.write(f"  [{a['id']}] {a['name']} (slug: {a['slug']})\n")

    f.write("\n" + "=" * 80 + "\n")
    f.write("PRODUCT TYPE DISTRIBUTION\n")
    f.write("=" * 80 + "\n")
    type_counts = {}
    for p in data['products']:
        t = p.get('type', 'unknown')
        type_counts[t] = type_counts.get(t, 0) + 1
    for t, c in sorted(type_counts.items()):
        f.write(f"  {t}: {c}\n")

    f.write("\n" + "=" * 80 + "\n")
    f.write("CATEGORY USAGE IN PRODUCTS\n")
    f.write("=" * 80 + "\n")
    cat_usage = {}
    for p in data['products']:
        for c in p.get('categories', []):
            cat_usage[c['name']] = cat_usage.get(c['name'], 0) + 1
    for name, count in sorted(cat_usage.items(), key=lambda x: -x[1]):
        f.write(f"  {name}: {count}\n")

    f.write("\n" + "=" * 80 + "\n")
    f.write("ATTRIBUTE USAGE IN PRODUCTS\n")
    f.write("=" * 80 + "\n")
    attr_usage = {}
    for p in data['products']:
        for a in p.get('attributes', []):
            attr_usage[a['name']] = attr_usage.get(a['name'], 0) + 1
    for name, count in sorted(attr_usage.items(), key=lambda x: -x[1]):
        f.write(f"  {name}: {count}\n")

    # Sample Products
    f.write("\n" + "=" * 80 + "\n")
    f.write("SAMPLE PRODUCTS (first 20)\n")
    f.write("=" * 80 + "\n")
    for p in data['products'][:20]:
        cats = ', '.join([c['name'] for c in p.get('categories', [])])
        f.write(f"\n  [{p['id']}] {p['name'][:70]}\n")
        f.write(f"      SKU: {p.get('sku', 'N/A')}\n")
        f.write(f"      Price: {p.get('price', 'N/A')} | Type: {p.get('type', 'N/A')}\n")
        f.write(f"      Categories: {cats}\n")
        f.write(f"      Variations: {len(p.get('variations', []))}\n")
        f.write(f"      Images: {len(p.get('images', []))}\n")

print("Analysis saved to analysis_output.txt")
