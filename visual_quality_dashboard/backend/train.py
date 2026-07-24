"""
train.py
========
Standalone script to train the eye-lens classifier.

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
        print("\n── Results ──────────────────────────────────")
        print(f"  Mean Accuracy : {stats['mean_accuracy']:.2%}")
        print(f"  Precision     : {stats['precision']:.2%}")
        print(f"  Recall        : {stats['recall']:.2%}")
        print(f"  F1-Score      : {stats['f1']:.2%}")
        print(f"  Fold scores   : {[f'{a:.2%}' for a in stats['fold_accuracies']]}")
        print(f"\n  Training data : {stats['n_good']} Good, {stats['n_damaged']} Damaged")
        print("\nModel saved to backend/model/classifier.pkl")
        print("Stats saved to backend/model/stats.json")
    except ValueError as e:
        print(f"\n[ERROR] {e}")
