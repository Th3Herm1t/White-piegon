"""
Configuration for WooCommerce Product Sync

This file contains mappings and settings for syncing products
from the FILLETTE V3.xlsx to WooCommerce.
"""

# API Configuration (loaded from .env)
import os

def load_env():
    """Load environment variables from .env file"""
    env_vars = {}
    env_path = os.path.join(os.path.dirname(__file__), '.env')
    if os.path.exists(env_path):
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if '=' in line and not line.startswith('#'):
                    key, value = line.split('=', 1)
                    env_vars[key.strip()] = value.strip()
    return env_vars

ENV = load_env()

# WooCommerce API Configuration
STORE_URL = ENV.get('STORE_URL', '').rstrip('/')
CONSUMER_KEY = ENV.get('Key', ENV.get('KEY', ''))
CONSUMER_SECRET = ENV.get('SECRET', ENV.get('Secret', ''))

# WordPress credentials for Media API
WP_USERNAME = ENV.get('WP_USERNAME', '')
WP_APP_PASSWORD = ENV.get('WP_APP_PASSWORD', '')

# API Base URL
API_BASE = f"{STORE_URL}/wp-json/wc/v3"

# ============================================================================
# ATTRIBUTE CONFIGURATION
# ============================================================================

# Using "Taille" attribute for French size labels (2-3, 3-4, etc.)
SIZE_ATTRIBUTE = {
    'id': 3,
    'name': 'Taille',
    'slug': 'pa_taille'
}

# Color attribute
COLOR_ATTRIBUTE = {
    'id': 6,
    'name': 'Couleur',
    'slug': 'pa_colors'
}

# Size columns in XLSX (column indices 9-16 map to these sizes)
SIZE_COLUMNS = {
    9: '2-3',
    10: '3-4',
    11: '4-5',
    12: '6-7',
    13: '7-8',
    14: '9-10',
    15: '11-12',
    16: '13-14'
}

# ============================================================================
# CATEGORY CONFIGURATION
# ============================================================================

# Main Fillette category
FILLETTE_CATEGORY_ID = 296

# Category mappings from XLSX FAMILLE to WooCommerce category IDs
# Format: 'XLSX_VALUE': [list of category IDs]
CATEGORY_MAPPING = {
    # JEANS family
    'PANTALON JEANS': [296, 298, 307],  # Fillette > Bas > Jeans
    'JUPE JEANS': [296, 298, 310],       # Fillette > Bas > Jupe
    
    # COTTON family  
    'PANTALON COTTON': [296, 298, 308],  # Fillette > Bas > Pantalons
    
    # HAUTS family
    'T-SHIRT': [296, 297, 301],          # Fillette > Hauts > T-shirts
    'PULL': [296, 297, 303],             # Fillette > Hauts > Pull
    'SWEAT': [296, 297, 305],            # Fillette > Hauts > Sweats
    
    # Default - just Fillette
    'DEFAULT': [296]
}

def get_categories_for_famille(famille):
    """Get WooCommerce category IDs for a FAMILLE value from XLSX"""
    if not famille:
        return CATEGORY_MAPPING['DEFAULT']
    
    famille_upper = famille.upper().strip()
    
    # Try exact match first
    if famille_upper in CATEGORY_MAPPING:
        return CATEGORY_MAPPING[famille_upper]
    
    # Try partial match
    for key, categories in CATEGORY_MAPPING.items():
        if key != 'DEFAULT' and key in famille_upper:
            return categories
    
    # Default to Fillette
    return CATEGORY_MAPPING['DEFAULT']

# ============================================================================
# XLSX COLUMN MAPPING
# ============================================================================

# Column indices in the XLSX file (0-indexed, after skipping header rows)
XLSX_COLUMNS = {
    'category_group': 0,    # e.g., JEANS, COTTON
    'famille': 1,           # e.g., PANTALON JEANS, JUPE JEANS
    'sku': 2,               # CODE ARTICLE (e.g., WPJF 001-127)
    'price': 3,             # Prix
    'name': 4,              # DESIGNATION
    'color_material': 5,    # COULEUR, MATIERE ET COMPOSITION
    'color': 6,             # COULEUR
    'tech_description': 7,  # DESCRIPTION TECHNIQUE PRODUIT
    'description': 8,       # DESCRIPTION COMMERCIALE PRODUIT
    # Sizes: columns 9-16
    'size_start': 9,
    'size_end': 16
}

# First data row (0-indexed) - skip header rows
XLSX_DATA_START_ROW = 4  # Row 5 in Excel (1-indexed)
XLSX_HEADER_ROW = 2      # Row 3 in Excel (1-indexed)

# ============================================================================
# SKU PARSING
# ============================================================================

def parse_sku(raw_sku):
    """
    Parse SKU to extract base product code and variation code.
    
    Examples:
        "WPJF 001-127" -> ("WPJF 001", "127")
        "WPJF 001 -120" -> ("WPJF 001", "120")
        "WPMF001 ROSE -39" -> ("WPMF001", "39")
        "WPJF 0012 BLUE MEDIUM" -> ("WPJF 0012", "BLUE MEDIUM")
    """
    import re
    
    if not raw_sku or str(raw_sku).strip() == '':
        return None, None
    
    sku = str(raw_sku).strip()
    sku = ' '.join(sku.split())
    
    # Try dash pattern first
    match = re.match(r'^(.+?)[\s]*-[\s]*(\d+)$', sku)
    if match:
        base, var = match.group(1).strip(), match.group(2).strip()
    else:
        # Try space pattern
        match = re.match(r'^(WP[A-Z]+\s*\d+)\s+(.+)$', sku)
        if match:
            base, var = match.group(1).strip(), match.group(2).strip()
        else:
            base, var = sku, None
            
    # Deep parse: if base still contains a space after the product part (e.g., "WPMF001 ROSE")
    if base and ' ' in base:
        deep_match = re.match(r'^(WP[A-Z]+\s*\d+)\s+(.+)$', base)
        if deep_match:
            base = deep_match.group(1).strip()
            # If we didn't have a var from the previous step, use the one from deep_match
            if var is None:
                var = deep_match.group(2).strip()
                
    return base, var

def get_base_sku(raw_sku):
    """Get just the base SKU without variation code"""
    base, _ = parse_sku(raw_sku)
    return base

def get_variation_code(raw_sku):
    """Get just the variation code"""
    _, code = parse_sku(raw_sku)
    return code

# ============================================================================
# SYNC SETTINGS
# ============================================================================

# Dry run mode - set to True to validate without creating products
DRY_RUN = False

# Skip products that already exist (by SKU)
SKIP_EXISTING = True

# Default product status
DEFAULT_STATUS = 'publish'  # 'publish', 'draft', 'pending', 'private'

# Stock management
MANAGE_STOCK = False  # Set to True if you want to track stock
DEFAULT_STOCK_STATUS = 'instock'

# ============================================================================
# IMAGE CONFIGURATION (placeholder for when images are provided)
# ============================================================================

# Base URL for images (to be configured when Google Drive links are provided)
IMAGE_BASE_URL = None  # e.g., 'https://drive.google.com/uc?export=view&id='

# Image column in XLSX (if any)
IMAGE_COLUMN = None

# Image naming convention (if images are named by SKU)
# Format: '{sku}_1.jpg', '{sku}_2.jpg', etc.
IMAGE_NAMING_PATTERN = None
