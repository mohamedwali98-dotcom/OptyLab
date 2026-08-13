"""
Image augmentation utilities for the OptyLab lens classifier.

This module provides transformations that simulate variations in lighting conditions
and other small changes that might affect classification. These augmentations help
make the classifier more robust and detect subtle damage patterns.
"""

import numpy as np
from PIL import Image, ImageEnhance, ImageFilter
import random
from pathlib import Path
from typing import List, Tuple, Optional

# Number of augmentations per image
NUM_AUGMENTATIONS = 5

# Random seed for reproducibility (None = random each time)
RANDOM_SEED = None


def get_augmentations(img_path: Path, num_augs: int = NUM_AUGMENTATIONS, seed: Optional[int] = RANDOM_SEED) -> List[Tuple[Path, str]]:
    """
    Generate augmented versions of an image for robust classification.
    
    Each augmentation applies subtle transformations to simulate:
    - Small brightness variations (detecting damage in different lighting)
    - Contrast changes
    - Slight rotations
    - Gaussian noise (to detect small defects)
    - Sharpening (enhancing details)
    
    Args:
        img_path: Path to the original image
        num_augs: Number of augmented versions to generate
        seed: Optional random seed for reproducibility
        
    Returns:
        List of tuples (temp_path, original_filename) for each augmentation
    """
    if seed is not None:
        random.seed(seed)
        np.random.seed(seed)
    
    img = Image.open(img_path).convert("RGB")
    augmentations = []
    temp_dir = Path("/tmp/optylab_augs")
    temp_dir.mkdir(parents=True, exist_ok=True)
    
    for i in range(num_augs):
        # Create a copy for each augmentation
        aug_img = img.copy()
        
        # Random brightness variation (factor around 1.0, ±15%)
        brightness_factor = 1.0 + random.uniform(-0.15, 0.15)
        aug_img = ImageEnhance.Brightness(aug_img).enhance(brightness_factor)
        
        # Random contrast variation (detects damage that might appear under different contrast)
        contrast_factor = 1.0 + random.uniform(-0.1, 0.15)
        aug_img = ImageEnhance.Contrast(aug_img).enhance(contrast_factor)
        
        # Small rotation (±5 degrees) to handle slight positioning variations
        if random.random() < 0.7:  # Apply rotation to 70% of augmentations
            angle = random.uniform(-5, 5)
            aug_img = aug_img.rotate(angle, resample=Image.BICUBIC, expand=False, fillcolor=None)
        
        # Add slight Gaussian blur to some augmentations (helps detect cracks/smudges)
        if random.random() < 0.3:
            aug_img = aug_img.filter(ImageFilter.GaussianBlur(radius=random.uniform(0.3, 1.0)))
        
        # Add slight sharpening to enhance potential damage
        if random.random() < 0.4:
            aug_img = aug_img.filter(ImageFilter.SHARPEN)
        
        # Add very subtle noise (helps detect small defects)
        if random.random() < 0.5:
            noise = np.random.randint(-8, 9, (aug_img.height, aug_img.width, 3))
            aug_arr = np.array(aug_img, dtype=np.int16)
            aug_arr = np.clip(aug_arr + noise, 0, 255).astype(np.uint8)
            aug_img = Image.fromarray(aug_arr)
        
        # Save augmentation
        stem = img_path.stem
        ext = img_path.suffix
        aug_path = temp_dir / f"{stem}_aug_{i:02d}{ext}"
        aug_img.save(aug_path, quality=95)
        augmentations.append((aug_path, img_path.name))
    
    return augmentations


def parse_group_id(filename: str) -> Optional[str]:
    """
    Extract group ID from filename if it exists.
    
    Group IDs are the part before the triple underscores.
    Example: "GROUP001___image.png" -> "GROUP001"
    
    Args:
        filename: The filename to parse
        
    Returns:
        Group ID if present, None otherwise
    """
    if "___" in filename:
        return filename.split("___", 1)[0]
    return None


def get_image_group(files: List[Path]) -> dict:
    """
    Group images by their group_id or filename.
    
    Args:
        files: List of image paths
        
    Returns:
        Dict mapping group_id -> list of file paths
    """
    groups = {}
    for f in files:
        group_id = parse_group_id(f.name)
        if group_id is None:
            group_id = f.name  # No group, use filename as group
        if group_id not in groups:
            groups[group_id] = []
        groups[group_id].append(f)
    return groups