import csv
import datetime
import sys
from pathlib import Path

# Allow running from scripts/ with the project root on sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from database import SessionLocal, init_db
import models


def import_wfp_prices(path: str):
    init_db()
    db = SessionLocal()
    try:
        user = db.query(models.User).first()
        if user is None:
            user = models.User(
                full_name="Demo Farmer",
                email="demo@example.com",
                username="demo_farmer",
                hashed_password="demo-password",
                role="farmer",
                is_validated=True,
                is_active=True,
            )
            db.add(user)
            db.flush()

        crop = db.query(models.Crop).filter(models.Crop.owner_id == user.id).first()
        if crop is None:
            crop = models.Crop(name="Culture importée", surface=3.0, owner_id=user.id)
            db.add(crop)
            db.flush()

        file_path = Path(path)
        if not file_path.exists():
            raise FileNotFoundError(f"Fichier introuvable: {path}")

        with file_path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            inserted = 0
            for row in reader:
                price = row.get("price") or row.get("Price") or row.get("value") or row.get("Value") or row.get("commodity_price")
                if not price:
                    continue
                market = row.get("market") or row.get("Market") or row.get("market_name") or row.get("location") or row.get("Location") or "Inconnu"
                commodity = row.get("commodity") or row.get("Commodity") or row.get("crop") or row.get("Crop") or "inconnu"
                try:
                    price_value = float(price)
                except Exception:
                    continue

                db.add(models.MarketPrice(
                    crop_type=str(commodity).lower(),
                    market_location=str(market),
                    price_per_kg=price_value,
                    currency="XOF",
                    source="wfp_csv",
                    timestamp=datetime.datetime.utcnow(),
                ))
                inserted += 1

            db.commit()
            print(f"{inserted} prix importés depuis {file_path}")
    finally:
        db.close()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/import_wfp_prices.py <fichier.csv>")
        raise SystemExit(1)
    import_wfp_prices(sys.argv[1])
