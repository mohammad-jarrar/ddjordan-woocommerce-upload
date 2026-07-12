# WooCommerce + Codex Product Upload Kit

This kit is built for uploading the optimized product catalog to WooCommerce with a Codex Agent.

## Files

- `data/ddjordan_magictech_woocommerce_seo_optimized.csv`  
  SEO-optimized WooCommerce-ready catalog.
- `data/source_ddjordan_magictech_current_categories_ready_import.csv`  
  Original source file for traceability.
- `scripts/validate_products.py`  
  Validates the CSV before upload.
- `scripts/upload_products.py`  
  Idempotent WooCommerce REST API uploader with dry-run mode.
- `.env.example`  
  Environment variables Codex needs.

## Recommended workflow in Codex

1. Put this kit in a GitHub repository.
2. Add the product images to one public folder on the website:
   `/wp-content/uploads/product_images/`
3. In Codex, add environment variables from `.env.example`.
4. Run validation first:
   ```bash
   python scripts/validate_products.py data/ddjordan_magictech_woocommerce_seo_optimized.csv
   ```
5. Run a dry run:
   ```bash
   DRY_RUN=1 python scripts/upload_products.py data/ddjordan_magictech_woocommerce_seo_optimized.csv
   ```
6. Upload for real only after the dry run passes:
   ```bash
   DRY_RUN=0 python scripts/upload_products.py data/ddjordan_magictech_woocommerce_seo_optimized.csv
   ```

## Required WordPress / WooCommerce settings

### WooCommerce REST API
Create API keys from:

WooCommerce → Settings → Advanced → REST API → Add key

Use:
- Permissions: Read/Write
- Store the values as:
  - `WC_CONSUMER_KEY`
  - `WC_CONSUMER_SECRET`

### Product images

Best method:
- Upload all images into:
  `/wp-content/uploads/product_images/`
- Set:
  `IMAGE_BASE_URL=https://yourdomain.com/wp-content/uploads/product_images/`

The uploader will convert image filenames into full URLs before sending them to WooCommerce.

### SEO plugin

The CSV includes fields for both:
- Rank Math
- Yoast SEO

The REST uploader writes both meta keys:
- `rank_math_title`
- `rank_math_description`
- `rank_math_focus_keyword`
- `_yoast_wpseo_title`
- `_yoast_wpseo_metadesc`

This lets you use either SEO plugin without rebuilding the file.

## What the uploader does

- Creates or updates products by SKU.
- Preserves stock status using WooCommerce-compatible `In stock?` values.
- Sends product name, slug, category, tags, descriptions, price, images, attributes, and SEO meta.
- Creates missing categories and tags through WooCommerce/WordPress REST where possible.
- Generates logs:
  - `upload_success.csv`
  - `upload_errors.csv`

## Safety

Default mode is dry-run. It will not change WooCommerce unless:

```bash
DRY_RUN=0
```

Run on staging first if possible.
