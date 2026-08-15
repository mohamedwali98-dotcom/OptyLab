"""
train.py
========
Standalone script to train the eye-lens classifier. This is a thin wrapper
around augment_and_train.py's training step (classifier.train_and_evaluate) —
it trains on whatever is already in DB/Good and DB/Damaged, without running
the augmentation step first. To also (re)generate augmented images from
DB/RawImages{Good,Damaged}, use augment_and_train.py instead.

Usage:
    cd visual_quality_dashboard/backend
    python train.py
"""

from classifier import train_and_evaluate

if __name__ == "__main__":
    print("=" * 60)
    print("OptyLab Eye Lens Classifier - Training")
    print("=" * 60)
    try:
        stats = train_and_evaluate()
        print("\n-- Results (held-out test set) -------------")
        print(f"  Ensemble Accuracy : {stats['ensemble_accuracy']:.2%}")
        print(f"  Precision         : {stats['precision']:.2%}")
        print(f"  Recall            : {stats['recall']:.2%}")
        print(f"  F1-Score          : {stats['f1']:.2%}")
        svm_acc, cnn_acc, vit_acc = stats['model_accuracies']
        print(f"  SVM / CNN / ViT   : {svm_acc:.2%} / {cnn_acc:.2%} / {vit_acc:.2%}")
        print(f"\n  Split : {stats['n_train']} train / {stats['n_val']} val / {stats['n_test']} test")
        print(f"  Data  : {stats['n_good']} Good, {stats['n_damaged']} Damaged")
        print("\nModel files saved to backend/model/")
        print("Stats saved to backend/model/stats.json")
    except ValueError as e:
        print(f"\n[ERROR] {e}")
