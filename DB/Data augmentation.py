import os
import cv2
import albumentations as A

# ---- EDIT THESE FOR YOUR SETUP -----------------------------------------
BASE_DIR = r"C:\Users\moham\Desktop\OptyLab\DB"
DIRS = [
    (os.path.join(BASE_DIR, "RawImagesGood"), os.path.join(BASE_DIR, "Good")),
    (os.path.join(BASE_DIR, "RawImagesDamaged"), os.path.join(BASE_DIR, "Damaged"))
]
AUGS_PER_IMAGE = 8   # how many augmented variants to generate per original photo
# -------------------------------------------------------------------------

# Full set of filters applied to 6 of the images
transform_full = A.Compose([
    A.Resize(224, 224),
    A.HorizontalFlip(p=0.5),
    A.Rotate(limit=15, p=0.5),
    A.RandomBrightnessContrast(p=0.4),
    A.GaussianBlur(blur_limit=(3, 5), p=0.3),
    A.GaussNoise(std_range=(0.01, 0.05), p=0.3),
])

# Rotation-only filters applied to the other 2 images
transform_rotate = A.Compose([
    A.Resize(224, 224),
    A.Rotate(limit=15, p=1.0),
])

VALID_EXTENSIONS = (".jpg", ".jpeg", ".png", ".bmp")


def main():
    for input_dir, output_dir in DIRS:
        # Create directories if they don't exist
        os.makedirs(input_dir, exist_ok=True)
        os.makedirs(output_dir, exist_ok=True)

        image_files = [f for f in os.listdir(input_dir) if f.lower().endswith(VALID_EXTENSIONS)]
        print(f"Found {len(image_files)} image(s) in {input_dir}")

        for fname in image_files:
            path = os.path.join(input_dir, fname)
            image = cv2.imread(path)
            if image is None:
                print(f"Skipping unreadable file: {fname}")
                continue
            image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

            name, ext = os.path.splitext(fname)
            for i in range(AUGS_PER_IMAGE):
                if i < 6:
                    augmented = transform_full(image=image)["image"]
                else:
                    augmented = transform_rotate(image=image)["image"]
                augmented_bgr = cv2.cvtColor(augmented, cv2.COLOR_RGB2BGR)
                out_name = f"{name}_aug{i + 1}{ext}"
                out_path = os.path.join(output_dir, out_name)
                cv2.imwrite(out_path, augmented_bgr)

            print(f"Saved {AUGS_PER_IMAGE} augmented version(s) of {fname}")

    print("Done. Augmented images have been saved to their respective directories.")


if __name__ == "__main__":
    main()