import json
import uuid
import random
from datetime import datetime, timezone
from pathlib import Path

# ── Config ────────────────────────────────────────────────────────────────────
BASE_DIR     = Path(__file__).parent
UPLOADS_DIR  = BASE_DIR / "uploads"
RESULTS_FILE = BASE_DIR / "results.json"

VALID = {".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".tif"}
# ─────────────────────────────────────────────────────────────────────────────


def random_entry(img_path: Path) -> dict:
    """Build a fake result row for one image."""
    prediction = random.choice(["Good", "Damaged"])
    # Confidence: Good → 0.60–0.99 | Damaged → 0.55–0.99
    confidence = round(random.uniform(0.55, 0.99), 4)
    ts = datetime.now(timezone.utc)
    return {
        "id":         f"OPY-{uuid.uuid4().hex[:6].upper()}",
        "filename":   img_path.name,
        "timestamp":  ts.isoformat(),
        "prediction": prediction,
        "confidence": confidence,
        "thumbnail":  True,          # tells the frontend to load /thumbnail/<filename>
    }


def main():
    # Collect images
    if not UPLOADS_DIR.exists():
        print(f"[!] Uploads folder not found: {UPLOADS_DIR}")
        print("    Upload some images via the dashboard first, then re-run this script.")
        return

    images = sorted(
        f for f in UPLOADS_DIR.iterdir()
        if f.is_file() and f.suffix.lower() in VALID
    )

    if not images:
        print("[!] No images found in uploads/.")
        print("    Upload some images via the dashboard first, then re-run this script.")
        return

    # Generate random results
    results = [random_entry(img) for img in images]

    # Write to results.json
    RESULTS_FILE.write_text(json.dumps(results, indent=2))

    # ── Pretty-print summary table ────────────────────────────────────────────
    col_w = [30, 12, 12, 10]
    header = (
        f"{'Filename':<{col_w[0]}} {'Prediction':<{col_w[1]}} "
        f"{'Confidence':<{col_w[2]}} {'ID':<{col_w[3]}}"
    )
    sep = "-" * sum(col_w)

    print("\n" + "=" * sum(col_w))
    print("  OptyLab — Mock Classification Results")
    print("=" * sum(col_w))
    print(header)
    print(sep)

    good_count    = 0
    damaged_count = 0
    for r in results:
        name  = r["filename"][:col_w[0] - 1]
        pred  = r["prediction"]
        conf  = f"{r['confidence'] * 100:.1f}%"
        rid   = r["id"]

        marker = "[OK]" if pred == "Good" else "[!!]"
        print(f"{name:<{col_w[0]}} {marker} {pred:<{col_w[1]-2}} {conf:<{col_w[2]}} {rid}")

        if pred == "Good":
            good_count += 1
        else:
            damaged_count += 1

    print(sep)
    print(f"  Total: {len(results)} image(s)  |  Good: {good_count}  |  Damaged: {damaged_count}")
    print(f"  Results saved -> {RESULTS_FILE}")
    print("=" * sum(col_w))
    print("\n  Refresh the Results tab in the dashboard to see the entries.\n")


if __name__ == "__main__":
    random.seed()   # true random every run
    main()
