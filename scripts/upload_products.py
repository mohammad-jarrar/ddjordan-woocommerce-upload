#!/usr/bin/env python3
"""
WooCommerce product uploader.

Features:
- Dry-run by default.
- Creates/updates products by SKU.
- Resolves image filenames with IMAGE_BASE_URL.
- Creates missing categories/tags.
- Uploads SEO meta for Rank Math and Yoast.
"""

import csv
import json
import os
import sys
import time
from urllib.parse import urljoin
from collections import defaultdict

import requests
from requests.auth import HTTPBasicAuth

def env_bool(name, default=False):
    val = os.getenv(name)
    if val is None:
        return default
    return val.strip().lower() in {"1", "true", "yes", "y", "on"}

WORDPRESS_URL = os.getenv("WORDPRESS_URL", "").rstrip("/")
WC_CONSUMER_KEY = os.getenv("WC_CONSUMER_KEY", "")
WC_CONSUMER_SECRET = os.getenv("WC_CONSUMER_SECRET", "")
IMAGE_BASE_URL = os.getenv("IMAGE_BASE_URL", "").rstrip("/") + "/" if os.getenv("IMAGE_BASE_URL") else ""
DRY_RUN = env_bool("DRY_RUN", True)
VERIFY_SSL = env_bool("VERIFY_SSL", True)
BATCH_SIZE = int(os.getenv("BATCH_SIZE", "50"))
DEFAULT_PRODUCT_STATUS = os.getenv("DEFAULT_PRODUCT_STATUS", "publish")

if not WORDPRESS_URL:
    print("ERROR: WORDPRESS_URL is required.")
    sys.exit(2)
if not WC_CONSUMER_KEY or not WC_CONSUMER_SECRET:
    print("ERROR: WC_CONSUMER_KEY and WC_CONSUMER_SECRET are required.")
    sys.exit(2)

WC_API = f"{WORDPRESS_URL}/wp-json/wc/v3"
WP_API = f"{WORDPRESS_URL}/wp-json/wp/v2"
AUTH = HTTPBasicAuth(WC_CONSUMER_KEY, WC_CONSUMER_SECRET)
SESSION = requests.Session()
SESSION.auth = AUTH
SESSION.verify = VERIFY_SSL
SESSION.headers.update({"User-Agent": "ddjordan-codex-woocommerce-uploader/1.0"})

category_cache = {}
tag_cache = {}

def request(method, url, **kwargs):
    if "timeout" not in kwargs:
        kwargs["timeout"] = 60
    resp = SESSION.request(method, url, **kwargs)
    if resp.status_code >= 400:
        raise RuntimeError(f"{method} {url} failed {resp.status_code}: {resp.text[:1000]}")
    if resp.text:
        return resp.json()
    return None

def read_csv(path):
    with open(path, newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))

def split_list(value):
    if not value:
        return []
    # CSV Images usually comma-separated; Woo multi-images can be pipe-separated too.
    parts = []
    for piece in str(value).replace("|", ",").split(","):
        piece = piece.strip()
        if piece:
            parts.append(piece)
    return parts

def image_to_src(value):
    value = value.strip()
    if not value:
        return None
    if value.startswith("http://") or value.startswith("https://"):
        return value
    if IMAGE_BASE_URL:
        return urljoin(IMAGE_BASE_URL, value)
    # WooCommerce may resolve filenames if they exist in wp-content/uploads/product_images/
    return value

def get_product_by_sku(sku):
    items = request("GET", f"{WC_API}/products", params={"sku": sku, "per_page": 1})
    return items[0] if items else None

def find_term(endpoint, name):
    data = request("GET", f"{WC_API}/{endpoint}", params={"search": name, "per_page": 100})
    for item in data:
        if item.get("name", "").strip().lower() == name.strip().lower():
            return item
    return None

def ensure_category_path(path):
    """
    WooCommerce categories are hierarchical.
    Input: "Parent > Child > Grandchild"
    Returns final category ID.
    """
    if not path:
        return None
    if path in category_cache:
        return category_cache[path]

    parent_id = None
    accumulated = []
    for part in [p.strip() for p in path.split(">") if p.strip()]:
        accumulated.append(part)
        cache_key = " > ".join(accumulated)
        if cache_key in category_cache:
            parent_id = category_cache[cache_key]
            continue

        existing = find_term("products/categories", part)
        if existing:
            parent_id = existing["id"]
        else:
            if DRY_RUN:
                print(f"[DRY-RUN] Would create category: {cache_key}")
                parent_id = -abs(hash(cache_key)) % 1000000
            else:
                payload = {"name": part}
                if parent_id and parent_id > 0:
                    payload["parent"] = parent_id
                created = request("POST", f"{WC_API}/products/categories", json=payload)
                parent_id = created["id"]
                print(f"Created category: {cache_key} -> {parent_id}")
        category_cache[cache_key] = parent_id
    category_cache[path] = parent_id
    return parent_id

def ensure_tag(name):
    name = name.strip()
    if not name:
        return None
    if name in tag_cache:
        return tag_cache[name]
    existing = find_term("products/tags", name)
    if existing:
        tag_cache[name] = existing["id"]
        return existing["id"]
    if DRY_RUN:
        print(f"[DRY-RUN] Would create tag: {name}")
        tag_cache[name] = -abs(hash(name)) % 1000000
        return tag_cache[name]
    created = request("POST", f"{WC_API}/products/tags", json={"name": name})
    tag_cache[name] = created["id"]
    return created["id"]

def meta_data_from_row(row):
    mapping = {
        "rank_math_title": row.get("Meta: rank_math_title") or row.get("SEO Title"),
        "rank_math_description": row.get("Meta: rank_math_description") or row.get("Meta Description"),
        "rank_math_focus_keyword": row.get("Meta: rank_math_focus_keyword"),
        "_yoast_wpseo_title": row.get("Meta: _yoast_wpseo_title") or row.get("SEO Title"),
        "_yoast_wpseo_metadesc": row.get("Meta: _yoast_wpseo_metadesc") or row.get("Meta Description"),
    }
    return [{"key": k, "value": v} for k, v in mapping.items() if v]

def attributes_from_row(row):
    attrs = []
    for i in range(1, 10):
        name = row.get(f"Attribute {i} name", "").strip()
        values = row.get(f"Attribute {i} value(s)", "").strip()
        visible = row.get(f"Attribute {i} visible", "1").strip()
        if name and values:
            attrs.append({
                "name": name,
                "visible": visible != "0",
                "variation": False,
                "options": [v.strip() for v in values.split("|") if v.strip()] or [values],
            })
    brand = row.get("Brands", "").strip()
    if brand and not any(a["name"].lower() == "brand" for a in attrs):
        attrs.append({"name": "Brand", "visible": True, "variation": False, "options": [brand]})
    return attrs

def row_to_product_payload(row):
    sku = row["SKU"].strip()
    category_id = ensure_category_path(row.get("Categories", ""))
    categories = [{"id": category_id}] if category_id and category_id > 0 else []
    tags = []
    for tag in split_list(row.get("Tags", "")):
        tag_id = ensure_tag(tag)
        if tag_id and tag_id > 0:
            tags.append({"id": tag_id})

    images = []
    for img in split_list(row.get("Images", "")):
        src = image_to_src(img)
        if src:
            images.append({"src": src, "name": row.get("Name", ""), "alt": row.get("Name", "")})

    payload = {
        "type": row.get("Type", "simple") or "simple",
        "status": DEFAULT_PRODUCT_STATUS,
        "name": row.get("Name", "").strip(),
        "slug": row.get("Slug", "").strip(),
        "sku": sku,
        "regular_price": str(row.get("Regular price", "")).strip(),
        "description": row.get("Description", ""),
        "short_description": row.get("Short description", ""),
        "tax_status": row.get("Tax status", "taxable") or "taxable",
        "manage_stock": False,
        "stock_status": "instock" if str(row.get("In stock?", "1")).strip() == "1" else "outofstock",
        "categories": categories,
        "tags": tags,
        "images": images,
        "attributes": attributes_from_row(row),
        "meta_data": meta_data_from_row(row),
    }
    return payload

def write_log(path, rows, fieldnames):
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

def main():
    if len(sys.argv) < 2:
        print("Usage: upload_products.py <products.csv>")
        sys.exit(2)

    csv_path = sys.argv[1]
    products = read_csv(csv_path)
    print(f"Loaded {len(products)} products")
    print(f"DRY_RUN={DRY_RUN}")
    print(f"WORDPRESS_URL={WORDPRESS_URL}")
    if IMAGE_BASE_URL:
        print(f"IMAGE_BASE_URL={IMAGE_BASE_URL}")

    success = []
    errors = []

    for idx, row in enumerate(products, start=1):
        sku = row.get("SKU", "").strip()
        try:
            if not sku:
                raise ValueError("Missing SKU")
            payload = row_to_product_payload(row)
            if DRY_RUN:
                print(f"[DRY-RUN] {idx}/{len(products)} {sku}: would upload/update {payload['name']}")
                success.append({"sku": sku, "action": "dry-run", "product_id": ""})
                continue

            existing = get_product_by_sku(sku)
            if existing:
                product_id = existing["id"]
                result = request("PUT", f"{WC_API}/products/{product_id}", json=payload)
                action = "updated"
            else:
                result = request("POST", f"{WC_API}/products", json=payload)
                product_id = result["id"]
                action = "created"

            success.append({"sku": sku, "action": action, "product_id": product_id})
            print(f"{idx}/{len(products)} {sku}: {action} #{product_id}")
            time.sleep(0.2)

        except Exception as exc:
            errors.append({"sku": sku, "error": str(exc)})
            print(f"ERROR {idx}/{len(products)} {sku}: {exc}", file=sys.stderr)

    write_log("upload_success.csv", success, ["sku", "action", "product_id"])
    write_log("upload_errors.csv", errors, ["sku", "error"])

    print(f"Success rows: {len(success)}")
    print(f"Error rows: {len(errors)}")
    if errors:
        print("Upload completed with errors. See upload_errors.csv.")
        sys.exit(1)

if __name__ == "__main__":
    main()
