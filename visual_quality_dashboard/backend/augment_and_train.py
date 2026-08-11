"""
augment_and_train.py
====================
One-shot pipeline for OptyLab:

  Step 1 — Augment
    Reads every image from  DB/RawImagesDamaged/
    Applies the physics-informed augmentation pipeline
    (PolarizingFilter + NarrowBandpass + Moire + standard flips/jitter)
    Writes N augmented copies per image into  DB/Damaged/

  Step 2 — (Optional) Augment Good
    If DB/RawImagesGood/ has images, augments those into DB/Good/ too.

  Step 3 — Train
    Trains the full ensemble (SVM + CNN + ViT) on
    DB/Good/ + DB/Damaged/  and saves the updated model files.

Usage (run from the project root OR from backend/):
    C:/Python314/python.exe visual_quality_dashboard/backend/augment_and_train.py
    -- or --
    cd visual_quality_dashboard/backend
    C:/Python314/python.exe augment_and_train.py

Optional env var:
    AUG_PER_IMAGE=12   number of augmented copies per raw image (default: 10)
"""

import os
import sys
import random
from pathlib import Path

# ── Make sure we can import sibling modules regardless of cwd ─────────────────
BACKEND_DIR = Path(__file__).resolve().parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# ── Paths ─────────────────────────────────────────────────────────────────────
DB_DIR          = BACKEND_DIR.parent.parent / "DB"
RAW_DAMAGED_DIR = DB_DIR / "RawImagesDamaged"
RAW_GOOD_DIR    = DB_DIR / "RawImagesGood"
DAMAGED_DIR     = DB_DIR / "Damaged"
GOOD_DIR        = DB_DIR / "Good"

VALID_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif"}

AUG_PER_IMAGE = int(os.environ.get("AUG_PER_IMAGE", 10))


# =============================================================================
# STEP 1 & 2 — AUGMENTATION
# =============================================================================

def _build_pil_pipeline():
    """
    Returns a callable that applies a random augmentation chain to a PIL Image.
    Uses standard PIL operations + the three physics-informed simulations from
    augmentations.py so the output can be saved directly as JPEG.
    """
    from PIL import Image, ImageFilter, ImageEnhance
    from augmentations import (
        PolarizingFilterSimulation,
        NarrowBandpassFilterSimulation,
        MoireDeflectometrySimulation,
    )

    def random_flip(img):
        if random.random() < 0.5:
            img = img.transpose(Image.FLIP_LEFT_RIGHT)
        if random.random() < 0.3:
            img = img.transpose(Image.FLIP_TOP_BOTTOM)
        return img

    def random_rotate(img):
        if random.random() < 0.6:
            angle = random.uniform(-20, 20)
            img = img.rotate(angle, expand=False, fillcolor=(128, 128, 128))
        return img

    def random_brightness_contrast(img):
        if random.random() < 0.7:
            img = ImageEnhance.Brightness(img).enhance(random.uniform(0.65, 1.45))
        if random.random() < 0.7:
            img = ImageEnhance.Contrast(img).enhance(random.uniform(0.65, 1.55))
        if random.random() < 0.4:
            img = ImageEnhance.Sharpness(img).enhance(random.uniform(0.5, 2.0))
        if random.random() < 0.3:
            img = ImageEnhance.Color(img).enhance(random.uniform(0.7, 1.4))
        return img

    def random_blur(img):
        if random.random() < 0.25:
            img = img.filter(ImageFilter.GaussianBlur(radius=random.uniform(0.5, 1.5)))
        return img

    def random_crop_zoom(img):
        """Zoom in by cropping 5-15% of the border, then resize back."""
        if random.random() < 0.4:
            w, h = img.size
            frac   = random.uniform(0.05, 0.15)
            left   = int(w * frac)
            top    = int(h * frac)
            right  = w - int(w * frac)
            bottom = h - int(h * frac)
            img = img.crop((left, top, right, bottom)).resize((w, h), Image.BICUBIC)
        return img

    # Physics-informed optical simulations
    polarizing = PolarizingFilterSimulation(
        p=0.45,
        hue_shift_range=(0, 360),
        intensity=0.40,
        gabor_freqs=[0.08, 0.15, 0.25],
        edge_dilate_px=14,
    )
    bandpass = NarrowBandpassFilterSimulation(
        p=0.45,
        channel=None,
        clahe_clip=3.5,
        background_suppress=0.50,
        cross_channel_leak=0.12,
    )
    moire = MoireDeflectometrySimulation(
        p=0.40,
        fringe_frequency=0.08,
        fringe_amplitude=0.12,
        warp_strength=9.0,
        warp_radius=22,
        n_warp_points=6,
    )

    def apply_all(img):
        img = random_flip(img)
        img = random_rotate(img)
        img = random_brightness_contrast(img)
        img = random_blur(img)
        img = random_crop_zoom(img)
        img = polarizing(img)
        img = bandpass(img)
        img = moire(img)
        return img

    return apply_all


def augment_folder(src_dir: Path, dst_dir: Path, n_per_image: int, label: str) -> int:
    """
    For every image in src_dir generate n_per_image augmented copies in dst_dir.
    Old _augN files from previous runs are removed first to stay consistent.
    Returns the total number of images written.
    """
    from PIL import Image

    dst_dir.mkdir(parents=True, exist_ok=True)

    src_files = sorted(f for f in src_dir.iterdir() if f.suffix.lower() in VALID_EXTS)
    if not src_files:
        print(f"  [WARN] No images found in {src_dir}. Skipping {label} augmentation.")
        return 0

    # Clear old augmented files so the folder matches the current raw data
    removed = sum(1 for f in dst_dir.iterdir() if "_aug" in f.stem and f.unlink() is None)
    if removed:
        print(f"  Cleared {removed} old augmented {label} images.")

    pipeline = _build_pil_pipeline()
    total    = 0

    for src in src_files:
        try:
            img = Image.open(src).convert("RGB")
        except Exception as exc:
            print(f"  [WARN] Cannot open {src.name}: {exc}")
            continue

        for i in range(1, n_per_image + 1):
            aug      = pipeline(img)
            out_path = dst_dir / f"{src.stem}_aug{i}.jpg"
            aug.save(out_path, "JPEG", quality=92)
            total   += 1

        print(f"  ✓  {src.name}  →  {n_per_image} copies")

    return total


# =============================================================================
# STEP 3 — TRAINING
# =============================================================================

def run_training() -> dict:
    from classifier import train_and_evaluate
    return train_and_evaluate()


# =============================================================================
# MAIN
# =============================================================================

def main():
    print()
    print("=" * 65)
    print("  OptyLab — Augment & Train Pipeline")
    print("=" * 65)

    # ── Step 1: Augment Damaged ───────────────────────────────────────────────
    print(f"\n[STEP 1/3]  Augmenting DAMAGED images  "
          f"({AUG_PER_IMAGE} copies per source image)")
    print(f"  Source : {RAW_DAMAGED_DIR}")
    print(f"  Output : {DAMAGED_DIR}")

    if not RAW_DAMAGED_DIR.exists():
        print(f"\n  [ERROR] {RAW_DAMAGED_DIR} does not exist. Aborting.")
        sys.exit(1)

    n_damaged = augment_folder(RAW_DAMAGED_DIR, DAMAGED_DIR, AUG_PER_IMAGE, "Damaged")
    print(f"\n  → {n_damaged} Damaged augmented images written.\n")

    # ── Step 2: Augment Good (if raw source exists) ───────────────────────────
    if RAW_GOOD_DIR.exists():
        raw_good = [f for f in RAW_GOOD_DIR.iterdir() if f.suffix.lower() in VALID_EXTS]
        if raw_good:
            print(f"[STEP 2/3]  Augmenting GOOD images  "
                  f"({AUG_PER_IMAGE} copies per source image)")
            print(f"  Source : {RAW_GOOD_DIR}")
            print(f"  Output : {GOOD_DIR}")
            n_good = augment_folder(RAW_GOOD_DIR, GOOD_DIR, AUG_PER_IMAGE, "Good")
            print(f"\n  → {n_good} Good augmented images written.\n")
        else:
            existing = len([f for f in GOOD_DIR.iterdir()
                            if f.suffix.lower() in VALID_EXTS]) if GOOD_DIR.exists() else 0
            print(f"[STEP 2/3]  RawImagesGood is empty — "
                  f"using {existing} existing Good images.\n")
    else:
        existing = len([f for f in GOOD_DIR.iterdir()
                        if f.suffix.lower() in VALID_EXTS]) if GOOD_DIR.exists() else 0
        print(f"[STEP 2/3]  No RawImagesGood folder — "
              f"using {existing} existing Good images.\n")

    # ── Step 3: Train ─────────────────────────────────────────────────────────
    print("[STEP 3/3]  Training ensemble model (SVM + CNN + ViT)…")
    print("  This may take several minutes. Please wait…\n")

    try:
        stats = run_training()
    except ValueError as exc:
        print(f"\n  [ERROR] Training failed: {exc}")
        sys.exit(1)

    # ── Print summary ─────────────────────────────────────────────────────────
    model_accs = stats.get("model_accuracies", [])
    svm_acc = f"{model_accs[0]:.2%}" if len(model_accs) > 0 else "N/A"
    cnn_acc = f"{model_accs[1]:.2%}" if len(model_accs) > 1 else "N/A"
    vit_acc = f"{model_accs[2]:.2%}" if len(model_accs) > 2 else "N/A"

    print()
    print("=" * 65)
    print("  DONE — MODEL UPDATED SUCCESSFULLY")
    print("=" * 65)
    print(f"  Training data  :  {stats['n_good']} Good  |  {stats['n_damaged']} Damaged")
    print(f"  Mean Accuracy  :  {stats['mean_accuracy']:.2%}")
    print(f"  Precision      :  {stats['precision']:.2%}")
    print(f"  Recall         :  {stats['recall']:.2%}")
    print(f"  F1-Score       :  {stats['f1']:.2%}")
    print(f"  SVM Accuracy   :  {svm_acc}")
    print(f"  CNN Accuracy   :  {cnn_acc}")
    print(f"  ViT Accuracy   :  {vit_acc}")
    print()
    print(f"  Model files    →  {BACKEND_DIR / 'model'}/")
    print(f"  Stats file     →  {BACKEND_DIR / 'model' / 'stats.json'}")
    print("=" * 65)
    print()


if __name__ == "__main__":
    main()
