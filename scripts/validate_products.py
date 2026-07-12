#!/usr/bin/env python3
import csv
import re
import sys
from collections import Counter

REQUIRED_COLUMNS = [
    "Type", "SKU", "Name", "Regular price", "In stock?", "Categories",
    "Description", "Short description", "Images", "Slug"
]

def read_csv(path):
    with open(path, newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))

def is_price(value):
    return bool(re.fullmatch(r"\d+(\.\d{1,3})?", str(value).strip()))

def main():
    if len(sys.argv) < 2:
        print("Usage: validate_products.py <products.csv>")
        sys.exit(2)

    path = sys.argv[1]
    rows = read_csv(path)
    if not rows:
        print("ERROR: CSV has no products.")
        sys.exit(1)

    headers = set(rows[0].keys())
    missing_cols = [c for c in REQUIRED_COLUMNS if c not in headers]
    if missing_cols:
        print("ERROR: Missing required columns:", ", ".join(missing_cols))
        sys.exit(1)

    errors = []
    warnings = []

    sku_counts = Counter()
    slug_counts = Counter()
    for i, row in enumerate(rows, start=2):
        sku = row.get("SKU", "").strip()
        name = row.get("Name", "").strip()
        slug = row.get("Slug", "").strip()
        price = row.get("Regular price", "").strip()
        stock = row.get("In stock?", "").strip()
        description = row.get("Description", "")
        meta = row.get("Meta Description", row.get("Meta: rank_math_description", "")).strip()

        if not sku:
            errors.append((i, "Missing SKU"))
        else:
            sku_counts[sku] += 1

        if not name:
            errors.append((i, f"{sku}: Missing product name"))
        elif len(name) > 100:
            warnings.append((i, f"{sku}: Product name is long ({len(name)} chars)"))

        if not slug:
            errors.append((i, f"{sku}: Missing slug"))
        else:
            slug_counts[slug] += 1

        if not is_price(price):
            errors.append((i, f"{sku}: Regular price is not numeric: {price!r}"))

        if stock not in {"0", "1"}:
            errors.append((i, f"{sku}: In stock? must be 1 or 0, got {stock!r}"))

        if description.count("<li>") < 6:
            warnings.append((i, f"{sku}: Description has fewer than 6 bullet points"))

        if meta and len(meta) > 160:
            warnings.append((i, f"{sku}: Meta description over 160 chars"))

    duplicate_skus = [sku for sku, count in sku_counts.items() if count > 1]
    duplicate_slugs = [slug for slug, count in slug_counts.items() if count > 1]
    if duplicate_skus:
        errors.append(("ALL", f"Duplicate SKUs: {', '.join(duplicate_skus[:20])}"))
    if duplicate_slugs:
        errors.append(("ALL", f"Duplicate slugs: {', '.join(duplicate_slugs[:20])}"))

    print(f"Products checked: {len(rows)}")
    print(f"Errors: {len(errors)}")
    print(f"Warnings: {len(warnings)}")

    if warnings:
        print("\nWarnings:")
        for item in warnings[:50]:
            print(f"- Row {item[0]}: {item[1]}")
        if len(warnings) > 50:
            print(f"... {len(warnings) - 50} more warnings")

    if errors:
        print("\nErrors:")
        for item in errors[:100]:
            print(f"- Row {item[0]}: {item[1]}")
        if len(errors) > 100:
            print(f"... {len(errors) - 100} more errors")
        sys.exit(1)

    print("Validation passed.")

if __name__ == "__main__":
    main()
