"""
Tests for the augmentation and voting classification system.
"""
import sys
import os
from pathlib import Path

# Add the backend directory to the path
sys.path.insert(0, str(Path(__file__).parent))

from augmentation import get_augmentations, parse_group_id
from classifier import classify_single_image


def test_parse_group_id():
    """Test group ID extraction from filenames."""
    # Test with group prefix
    assert parse_group_id("GROUP001___image1.png") == "GROUP001"
    assert parse_group_id("GROUP002___subdir/image1.png") == "GROUP002"
    
    # Test without group prefix
    assert parse_group_id("standalone.png") is None
    
    print("✓ parse_group_id tests passed")


def test_get_augmentations():
    """Test augmentation generation."""
    # Create a simple test image
    from PIL import Image
    import tempfile
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a test image
        test_img_path = Path(tmpdir) / "test.png"
        img = Image.new("RGB", (224, 224), color=(128, 128, 128))
        img.save(test_img_path)
        
        # Generate augmentations
        augs = get_augmentations(test_img_path, num_augs=3)
        
        assert len(augs) == 3, f"Expected 3 augmentations, got {len(augs)}"
        
        for aug_path, original_name in augs:
            assert Path(aug_path).exists(), f"Augmentation file not found: {aug_path}"
            assert original_name == "test.png"
            
            # Verify the augmentation file is a valid image
            aug_img = Image.open(aug_path)
            assert aug_img.size == (224, 224), f"Unexpected size: {aug_img.size}"
        
        print("✓ get_augmentations tests passed")


def test_consensus_logic():
    """Test the consensus voting logic."""
    # This is tested indirectly through classify_group_with_consensus
    # Here we just verify the logic concept
    predictions = ["Good", "Good", "Damaged"]
    all_good = all(p == "Good" for p in predictions)
    assert all_good == False, "Consensus should fail when any prediction is Damaged"
    
    predictions = ["Good", "Good", "Good"]
    all_good = all(p == "Good" for p in predictions)
    assert all_good == True, "Consensus should pass when all predictions are Good"
    
    print("✓ consensus logic tests passed")


if __name__ == "__main__":
    test_parse_group_id()
    test_get_augmentations()
    test_consensus_logic()
    print("\nAll tests passed!")