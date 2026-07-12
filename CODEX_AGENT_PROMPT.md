# Codex Agent Prompt — WooCommerce SEO Product Upload

You are working on my WooCommerce product upload project.

Goal:
Upload the optimized product catalog to my WooCommerce website in the cleanest, safest, and most SEO-complete way possible.

Use the files in this repo:
- `data/ddjordan_magictech_woocommerce_seo_optimized.csv`
- `scripts/validate_products.py`
- `scripts/upload_products.py`

Important requirements:
1. Do not upload anything until validation and dry-run pass.
2. Do not create duplicate products. Products must be matched by SKU.
3. Preserve stock status:
   - `In stock? = 1` means `instock`
   - `In stock? = 0` means `outofstock`
4. Product names must stay SEO-focused:
   - brand + model + main product keyword
   - no stuffed supplier-style text
5. Keep all SEO meta:
   - Rank Math title/description/focus keyword
   - Yoast title/meta description
6. Keep categories exactly as hierarchical WooCommerce categories.
7. Resolve image filenames using `IMAGE_BASE_URL`.
8. If images fail, do not guess. Produce a CSV of failed SKUs and image filenames.
9. Create/update products only after I confirm dry-run results if running in an interactive Codex session.
10. Produce final reports:
    - uploaded products
    - failed products
    - duplicate/missing fields
    - image failures
    - categories/tags created

Steps:
1. Install dependencies:
   `pip install -r requirements.txt`
2. Run:
   `python scripts/validate_products.py data/ddjordan_magictech_woocommerce_seo_optimized.csv`
3. Run dry-run:
   `DRY_RUN=1 python scripts/upload_products.py data/ddjordan_magictech_woocommerce_seo_optimized.csv`
4. Review output. If clean, run:
   `DRY_RUN=0 python scripts/upload_products.py data/ddjordan_magictech_woocommerce_seo_optimized.csv`
5. Report exactly what happened and attach/upload the generated CSV logs.

Environment variables I will provide:
- `WORDPRESS_URL`
- `WC_CONSUMER_KEY`
- `WC_CONSUMER_SECRET`
- `IMAGE_BASE_URL`
- `DRY_RUN`
- `BATCH_SIZE`

Treat the store as production. Be careful, idempotent, and verification-first.
