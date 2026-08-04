"""
gradcam.py — damage localization for the OptyLab lens classifier.

Produces a Grad-CAM heatmap from the trained ResNet18 CNN, highlighting the
image regions the model uses for its prediction. We explain the PREDICTED
class (what the model actually decided) so the heatmap is always meaningful:
if the lens is classified "Damaged", the hot region is where the model saw the
defect; if "Good", the hot region is what it read as clean.

The heatmap is blended over the ORIGINAL image with a jet-style colormap
(blue→cyan→yellow→red, hottest = red) and the hottest connected region is
outlined with a red bounding box so the operator can spot the damage at a glance.

No new pip deps: torch / torchvision / numpy / PIL only.
"""

import numpy as np
import torch
import torch.nn.functional as F
from PIL import Image, ImageFilter, ImageDraw
from pathlib import Path

from classifier_utils import DEVICE, pytorch_transform


def _raw_cam(model, img_pil, target_class: int):
    """Return a normalized 2D numpy heatmap (0..1) for `target_class` by hooking
    the last conv block (ResNet18 layer4). Returns None if the gradient signal
    is degenerate (e.g. model is certain it is NOT that class)."""
    activations = {}
    gradients = {}

    def fwd_hook(module, inp, out):
        activations['value'] = out.detach()

    def bwd_hook(module, grad_in, grad_out):
        gradients['value'] = grad_out[0].detach()

    target_layer = model.layer4
    h1 = target_layer.register_forward_hook(fwd_hook)
    h2 = target_layer.register_full_backward_hook(bwd_hook)

    input_tensor = pytorch_transform(img_pil).unsqueeze(0).to(DEVICE)
    model.zero_grad()
    out = model(input_tensor)
    if hasattr(out, 'logits'):
        out = out.logits
    out = out.squeeze()

    if out.dim() == 0:
        score = out
    else:
        score = out[target_class]

    model.zero_grad()
    score.backward(retain_graph=True)
    h1.remove(); h2.remove()

    act = activations['value']     # (1, C, h, w)
    grad = gradients['value']      # (1, C, h, w)
    weights = grad.mean(dim=(2, 3), keepdim=True)
    cam = F.relu((weights * act).sum(dim=1, keepdim=True)).squeeze().cpu().numpy()

    cam = cam - cam.min()
    if cam.max() <= 1e-8:
        return None  # no signal (model sure it's not this class)
    cam = cam / cam.max()
    return cam


def _hotspot_box(cam, threshold=0.5):
    """Bounding box (cam-grid coords) around cam > threshold, padded.

    Returns (top, left, bottom, right) in the CAM grid coordinate frame.
    Used for a coarse initial region; the precise ellipse is computed later
    from the full-resolution mask in generate_damage_overlay.
    """
    h, w = cam.shape
    mask = cam > threshold
    if not mask.any():
        y, x = np.unravel_index(np.argmax(cam), cam.shape)
        r = max(1, h // 6)
        mask = np.zeros_like(cam, dtype=bool)
        mask[max(0, y - r):min(h, y + r), max(0, x - r):min(w, x + r)] = True
    ys, xs = np.where(mask)
    pad = max(1, h // 10)
    return (max(0, ys.min() - pad), max(0, xs.min() - pad),
            min(h - 1, ys.max() + pad), min(w - 1, xs.max() + pad))


def _ellipse_from_mask(mask):
    """Tightly-fit ellipse (in mask pixel space) around connected hot regions.

    `mask` is a boolean array at the resolution of the overlay. We compute the
    minimum-area rotated bounding ellipse of the largest connected hot blob so
    the red circle hugs the actual damage rather than a padded rectangle.
    """
    from scipy import ndimage as ndi

    # Keep only the largest connected hot region to avoid stray far-away pixels
    # (e.g. a secondary low-activation lobe) inflating the circle.
    labeled, n = ndi.label(mask)
    if n == 0:
        return None
    sizes = ndi.sum(np.ones_like(labeled), labeled, index=range(1, n + 1))
    largest = int(np.argmax(sizes)) + 1
    blob = labeled == largest

    ys, xs = np.where(blob)
    if len(xs) < 4:
        # Degenerate blob: fall back to a small circle centred on its mean.
        cy, cx = (ys.mean() if len(ys) else mask.shape[0] // 2,
                  xs.mean() if len(xs) else mask.shape[1] // 2)
        r = max(mask.shape) * 0.04
        return (cx - r, cy - r, cx + r, cy + r)

    # Bounding box of the largest blob (tight, no padding).
    x0, x1 = xs.min(), xs.max()
    y0, y1 = ys.min(), ys.max()

    # Slight inward snug: shrink to the 90th-percentile extent so fringe pixels
    # (CAM tail) don't blow the circle up. Cheap and makes it read as "precise".
    if len(xs) > 16:
        x0 = int(np.percentile(xs, 5))
        x1 = int(np.percentile(xs, 95))
        y0 = int(np.percentile(ys, 5))
        y1 = int(np.percentile(ys, 95))

    # Convert the tight bbox into a CIRCLE that encloses it (ellipse).
    cx = (x0 + x1) / 2.0
    cy = (y0 + y1) / 2.0
    rx = (x1 - x0) / 2.0
    ry = (y1 - y0) / 2.0
    return (cx, cy, rx, ry)


def generate_damage_overlay(model, img_path: Path, predicted_class: int = 1,
                            alpha: float = 0.6):
    """
    Build a damage-localization overlay for one image.

    `predicted_class`: 1 = Damaged, 0 = Good (pass the model's prediction so the
    CAM explains the actual decision). Returns PIL.Image(RGB) or None on failure.
    """
    try:
        img_pil = Image.open(img_path).convert("RGB")
        cam = _raw_cam(model, img_pil, predicted_class)
        if cam is None:
            return None

        # Upsample + smooth for a clean overlay.
        cam_img = Image.fromarray((cam * 255).astype(np.uint8)).resize(
            img_pil.size, Image.BICUBIC)
        cam_img = cam_img.filter(ImageFilter.GaussianBlur(
            radius=max(3, min(img_pil.size) // 80)))
        cam_arr = np.array(cam_img, dtype=np.float32) / 255.0

        # Vectorized jet-style colormap (blue→cyan→yellow→red), no per-pixel loop.
        t = cam_arr
        r = np.clip(1.5 - np.abs(4 * t - 3), 0, 1)
        g = np.clip(1.5 - np.abs(4 * t - 2), 0, 1)
        b = np.clip(1.5 - np.abs(4 * t - 1), 0, 1)
        heat = np.stack([r, g, b], axis=-1) * 255.0

        base = np.array(img_pil, dtype=np.float32)
        overlay = base * (1 - alpha * cam_arr[..., None]) + heat * (alpha * cam_arr[..., None])
        overlay = np.clip(overlay, 0, 255).astype(np.uint8)
        overlay_pil = Image.fromarray(overlay).convert("RGB")

        # Bounding box around the hotspot, mapped to original resolution.
        # We compute the precise hotspot at FULL overlay resolution (not the
        # coarse CAM grid) so the red circle hugs the actual damage tightly.
        oh, ow = img_pil.size[1], img_pil.size[0]

        # Full-res hot mask (same res as the blend overlay we already built).
        full_mask = cam_arr > 0.5
        ellipse = _ellipse_from_mask(full_mask)
        if ellipse is None:
            # Fallback to the coarse grid box if the mask is empty.
            t, l, b, r = _hotspot_box(cam)
            ch, cw = cam.shape
            y1, y2 = int(t / ch * oh), int(b / ch * oh)
            x1, x2 = int(l / cw * ow), int(r / cw * ow)
            y1, y2 = max(0, y1), min(oh, y2)
            x1, x2 = max(0, x1), min(ow, x2)
            cx, cy, rx, ry = (x1 + x2) / 2, (y1 + y2) / 2, (x2 - x1) / 2, (y2 - y1) / 2
        else:
            cx, cy, rx, ry = ellipse
            # Map from overlay (full) res → original image res.
            sx, sy = ow / cam_arr.shape[1], oh / cam_arr.shape[0]
            cx, cy = cx * sx, cy * sy
            rx, ry = rx * sx, ry * sy

        # Snug the radius so the circle tightly encircles the damage.
        rx *= 0.92
        ry *= 0.92

        draw = ImageDraw.Draw(overlay_pil)
        px = max(3, min(overlay_pil.size) // 110)
        Red = (255, 32, 24)
        # circle / ellipse centred at (cx, cy) with radii (rx, ry)
        draw.ellipse(
            [cx - rx, cy - ry, cx + rx, cy + ry],
            outline=Red, width=px,
        )
        return overlay_pil
    except Exception as e:
        print(f"[WARN] Grad-CAM failed for {img_path.name}: {e}")
        import traceback
        traceback.print_exc()
        return None
