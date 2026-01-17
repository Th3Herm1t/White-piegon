"""
Image Mapping Utilities

Provides robust matching between XLSX SKUs and image folder names,
handling various naming inconsistencies.
"""

import os
import re
from pathlib import Path

# Image directory
IMAGES_DIR = './images/FILLETTE----20260115T135436Z-1-001/FILLETTE---'


def normalize_sku(raw_sku):
    """
    Normalize an XLSX SKU to match folder naming convention.
    
    Handles:
    - Spaces: 'WPJF 001 -120' -> 'WPJF001-120'
    - Double spaces: 'WPJF 0051  FASHION' -> 'WPJF0051-FASHION'
    - Various dash patterns: 'WPJF 008- 141' -> 'WPJF008-141'
    - Slash separators: 'WPCHF001 /C1' -> 'WPCHF001-C1'
    - Text variation codes: 'WPJF 0012 BLUE MEDIUM' -> 'WPJF0012-BLUEMEDIUM'
    
    Returns: (normalized_sku, base_sku, variation_code)
    """
    if not raw_sku or str(raw_sku).strip() == '':
        return None, None, None
    
    sku = str(raw_sku).strip()
    
    # Normalize multiple spaces to single space
    sku = ' '.join(sku.split())
    
    # Convert slashes to dashes for consistency
    sku = sku.replace('/', '-')
    
    # Remove spaces around dashes
    sku = re.sub(r'\s*-\s*', '-', sku)
    
    # Pattern 1: SKU with dash and variation (e.g., "WPJF001-127" or "WPCHF001-C1")
    match = re.match(r'^(WP[A-Z]+)\s*(\d+)-(.+)$', sku)
    if match:
        prefix = match.group(1)
        number = match.group(2)
        variation = match.group(3).strip()
        
        base_sku = f"{prefix}{number}"
        normalized = f"{base_sku}-{variation}"
        
        return normalized, base_sku, variation
    
    # Pattern 2: SKU with space-separated variation (e.g., "WPJF 0012 BLUE MEDIUM")
    match = re.match(r'^(WP[A-Z]+)\s*(\d+)\s+(.+)$', sku)
    if match:
        prefix = match.group(1)
        number = match.group(2)
        variation = match.group(3).strip()
        
        base_sku = f"{prefix}{number}"
        normalized = f"{base_sku}-{variation}"
        
        return normalized, base_sku, variation
    
    # Pattern 3: SKU without variation (e.g., "WPJF 0015")
    match = re.match(r'^(WP[A-Z]+)\s*(\d+)$', sku)
    if match:
        prefix = match.group(1)
        number = match.group(2)
        
        base_sku = f"{prefix}{number}"
        
        return base_sku, base_sku, None
    
    # Fallback: just remove spaces
    normalized = sku.replace(' ', '')
    return normalized, normalized, None


def get_folder_key(folder_name):
    """
    Normalize a folder name for matching.
    Removes spaces, converts to uppercase for comparison.
    Also handles suffixes like " (1)", " (2)" often added by duplicates.
    """
    # Remove suffix like " (1)" or " (2)"
    clean_name = re.sub(r'\s*\(\d+\)$', '', folder_name)
    return clean_name.replace(' ', '').upper()


def scan_image_folders(images_dir=IMAGES_DIR):
    """
    Scan the images directory and build a mapping of normalized keys to folder paths.
    
    Returns: {normalized_key: folder_path}
    """
    if not os.path.exists(images_dir):
        return {}
    
    folders = {}
    for item in os.listdir(images_dir):
        item_path = os.path.join(images_dir, item)
        if os.path.isdir(item_path):
            key = get_folder_key(item)
            folders[key] = {
                'path': item_path,
                'name': item,
                'images': []
            }
            
            # List images in folder
            for f in os.listdir(item_path):
                if f.lower().endswith(('.jpg', '.jpeg', '.png', '.webp', '.gif')):
                    folders[key]['images'].append(os.path.join(item_path, f))
    
    return folders


def find_images_for_sku(raw_sku, folder_map):
    """
    Find image files for a given SKU.
    
    Uses fuzzy matching to handle naming inconsistencies.
    
    Returns: list of image file paths, or empty list if no match
    """
    if not raw_sku:
        return []
    
    normalized, base_sku, variation = normalize_sku(raw_sku)
    if not normalized:
        return []
    
    # Try exact match first
    key = normalized.replace(' ', '').upper()
    if key in folder_map:
        return folder_map[key]['images']
    
    # Try without spaces in variation
    if variation:
        key_no_space = f"{base_sku}-{variation.replace(' ', '')}".upper()
        if key_no_space in folder_map:
            return folder_map[key_no_space]['images']
    
    # Try base SKU only (for products without variation images)
    if base_sku:
        base_key = base_sku.upper()
        if base_key in folder_map:
            return folder_map[base_key]['images']
    
    # Try partial matching - find folder that starts with base SKU
    if base_sku:
        for folder_key, folder_info in folder_map.items():
            if folder_key.startswith(base_sku.upper()):
                return folder_info['images']
    
    return []


def build_sku_to_images_mapping(xlsx_skus, images_dir=IMAGES_DIR):
    """
    Build a complete mapping from XLSX SKUs to image paths.
    
    Args:
        xlsx_skus: List of dicts with 'raw_sku' key
        images_dir: Path to images directory
    
    Returns: {raw_sku: [image_paths]}
    """
    folder_map = scan_image_folders(images_dir)
    mapping = {}
    
    for sku_info in xlsx_skus:
        raw_sku = sku_info.get('raw_sku', '')
        images = find_images_for_sku(raw_sku, folder_map)
        mapping[raw_sku] = images
    
    return mapping


# Test
if __name__ == '__main__':
    # Test normalization
    test_skus = [
        'WPJF 001 -120',
        'WPJF 001-127',
        'WPJF 008- 141',
        'WPJF 0012 BLUE MEDIUM',
        'WPJF 0051  FASHION',
        'WPGR 001   -226',
        'WPJF 0015',
        'WPCHF001-C1',
    ]
    
    print("SKU Normalization Test")
    print("=" * 80)
    print(f"{'Raw SKU':<30} {'Normalized':<25} {'Base':<15} {'Variation':<15}")
    print("-" * 85)
    
    for sku in test_skus:
        normalized, base, var = normalize_sku(sku)
        print(f"{sku:<30} {normalized or 'N/A':<25} {base or 'N/A':<15} {var or 'N/A':<15}")
    
    # Test folder scanning
    print("\n\nFolder Scanning Test")
    print("=" * 80)
    
    folder_map = scan_image_folders()
    print(f"Found {len(folder_map)} image folders")
    
    for key, info in sorted(folder_map.items()):
        print(f"  {key}: {info['name']} ({len(info['images'])} images)")
    
    # Test matching
    print("\n\nSKU to Image Matching Test")
    print("=" * 80)
    
    for sku in test_skus:
        images = find_images_for_sku(sku, folder_map)
        status = f"{len(images)} images" if images else "NO MATCH"
        print(f"{sku:<30} -> {status}")
