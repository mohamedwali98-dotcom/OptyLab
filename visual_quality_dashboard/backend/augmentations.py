import random
import math

import numpy as np
from PIL import Image, ImageFilter, ImageEnhance, ImageDraw
import cv2  # OpenCV — already available via scikit-image dependency chain


# ─────────────────────────────────────────────────────────────────────────────
# Utility helpers
# ─────────────────────────────────────────────────────────────────────────────

def _pil_to_np(img: Image.Image) -> np.ndarray:
    """Convert PIL Image (RGB) → float32 numpy array in [0, 1]."""
    return np.asarray(img, dtype=np.float32) / 255.0


def _np_to_pil(arr: np.ndarray) -> Image.Image:
    """Convert float32 numpy array in [0, 1] → PIL Image (RGB, uint8)."""
    clipped = np.clip(arr, 0.0, 1.0)
    return Image.fromarray((clipped * 255).astype(np.uint8), mode="RGB")


def _detect_edge_mask(gray: np.ndarray, low: int = 40, high: int = 120) -> np.ndarray:
    """
    Canny edge detection on a uint8 grayscale image.
    Returns a float32 mask in [0, 1] where edges = 1.
    """
    edges = cv2.Canny(gray, low, high)
    return edges.astype(np.float32) / 255.0


def _dilate_mask(mask: np.ndarray, radius: int = 12) -> np.ndarray:
    """
    Dilate a binary float mask with a circular kernel.
    Grows the defect-edge region so effects bleed slightly beyond the edge.
    """
    kernel = cv2.getStructuringElement(
        cv2.MORPH_ELLIPSE, (2 * radius + 1, 2 * radius + 1)
    )
    dilated = cv2.dilate((mask * 255).astype(np.uint8), kernel)
    return dilated.astype(np.float32) / 255.0


def _gaussian_blur_mask(mask: np.ndarray, sigma: int = 15) -> np.ndarray:
    """Smooth a mask with a Gaussian blur to create soft feathered blending."""
    blurred = cv2.GaussianBlur(mask, (0, 0), sigmaX=sigma, sigmaY=sigma)
    return np.clip(blurred, 0.0, 1.0)


# ─────────────────────────────────────────────────────────────────────────────
# 1. Polarizing Filter Simulation (Birefringence / Stress Detection)
# ─────────────────────────────────────────────────────────────────────────────

class PolarizingFilterSimulation:

    def __init__(
        self,
        p: float = 0.5,
        hue_shift_range: tuple = (0, 360),
        intensity: float = 0.45,
        gabor_freqs: list = None,
        edge_dilate_px: int = 14,
    ):
        self.p = p
        self.hue_shift_range = hue_shift_range
        self.intensity = intensity
        self.gabor_freqs = gabor_freqs if gabor_freqs is not None else [0.1, 0.2]
        self.edge_dilate_px = edge_dilate_px

    def _build_spectral_overlay(self, h: int, w: int, base_hue: float) -> np.ndarray:
        """
        Create an H×W×3 RGB spectral (rainbow) overlay in float32 [0,1].
        The hue sweeps across the image width, starting at base_hue.
        """
        hue_sweep = np.linspace(base_hue, base_hue + 270, w, dtype=np.float32) % 360
        hue_row = hue_sweep[np.newaxis, :] / 360.0          # shape (1, W)
        hue_full = np.tile(hue_row, (h, 1))                  # shape (H, W)

        # Full saturation, high value → vivid spectral colors
        saturation = np.ones((h, w), dtype=np.float32)
        value      = np.ones((h, w), dtype=np.float32)

        # Stack and convert HSV→RGB via OpenCV
        hsv = np.stack([hue_full * 179, saturation * 255, value * 255], axis=2).astype(np.uint8)
        rgb = cv2.cvtColor(hsv, cv2.COLOR_HSV2RGB).astype(np.float32) / 255.0
        return rgb

    def _gabor_edge_boost(self, gray_u8: np.ndarray) -> np.ndarray:
        """
        Apply a bank of Gabor filters at multiple orientations and frequencies
        to reinforce fine structural edges (cracks, scratches).
        Returns a float32 response map [0, 1].
        """
        response = np.zeros_like(gray_u8, dtype=np.float32)
        for freq in self.gabor_freqs:
            for theta_deg in range(0, 180, 45):
                theta = math.radians(theta_deg)
                kernel, _ = cv2.getGaborKernel(
                    ksize=(21, 21),
                    sigma=4.0,
                    theta=theta,
                    lambd=1.0 / freq,
                    gamma=0.5,
                    psi=0,
                    ktype=cv2.CV_32F,
                )
                filtered = cv2.filter2D(gray_u8.astype(np.float32), cv2.CV_32F, kernel)
                response = np.maximum(response, np.abs(filtered))
        # Normalise to [0, 1]
        max_val = response.max()
        if max_val > 0:
            response /= max_val
        return response

    def __call__(self, img: Image.Image) -> Image.Image:
        if random.random() > self.p:
            return img

        arr = _pil_to_np(img)
        h, w = arr.shape[:2]

        # ── 1. Grayscale for edge detection ──────────────────────────────────
        gray_u8 = (cv2.cvtColor((arr * 255).astype(np.uint8), cv2.COLOR_RGB2GRAY))

        # ── 2. Build a combined edge mask (Canny + Gabor) ────────────────────
        canny_mask  = _detect_edge_mask(gray_u8, low=30, high=100)
        gabor_boost = self._gabor_edge_boost(gray_u8)

        # Combine: either strong Canny edge OR strong Gabor response
        combined_mask = np.clip(canny_mask + gabor_boost * 0.6, 0.0, 1.0)
        combined_mask = _dilate_mask(combined_mask, radius=self.edge_dilate_px)
        # Soft feathering so the spectral glow radiates outward like real birefringence
        combined_mask = _gaussian_blur_mask(combined_mask, sigma=self.edge_dilate_px)
        mask3 = combined_mask[:, :, np.newaxis]               # (H, W, 1) for broadcasting

        # ── 3. Build spectral overlay ─────────────────────────────────────────
        base_hue = random.uniform(*self.hue_shift_range)
        spectral = self._build_spectral_overlay(h, w, base_hue)

        # ── 4. Blend: spectral only where mask is hot, scaled by intensity ────
        alpha = mask3 * self.intensity
        result = arr * (1.0 - alpha) + spectral * alpha

        return _np_to_pil(result)


# ─────────────────────────────────────────────────────────────────────────────
# 2. Narrow Bandpass Filter Simulation (Dark-Field Contrast Maximization)
# ─────────────────────────────────────────────────────────────────────────────

class NarrowBandpassFilterSimulation:


    CHANNEL_IDX = {"red": 0, "green": 1, "blue": 2}

    def __init__(
        self,
        p: float = 0.5,
        channel=None,
        clahe_clip: float = 3.0,
        background_suppress: float = 0.55,
        cross_channel_leak: float = 0.15,
    ):
        self.p = p
        self.channel = channel
        self.clahe_clip = clahe_clip
        self.background_suppress = background_suppress
        self.cross_channel_leak = cross_channel_leak

        self._clahe = cv2.createCLAHE(clipLimit=clahe_clip, tileGridSize=(8, 8))

    def __call__(self, img: Image.Image) -> Image.Image:
        if random.random() > self.p:
            return img

        arr_u8 = np.asarray(img, dtype=np.uint8).copy()   # (H, W, 3) uint8 RGB

        # ── 1. Choose bandpass channel ────────────────────────────────────────
        ch_name = self.channel or random.choice(["green", "red"])
        ch_idx  = self.CHANNEL_IDX[ch_name]
        band    = arr_u8[:, :, ch_idx].copy()              # isolated channel uint8

        # ── 2. CLAHE: enhance local contrast inside crack regions ─────────────
        band_clahe = self._clahe.apply(band)               # still uint8

        # ── 3. Adaptive background suppression ───────────────────────────────
        # Compute a pixel-wise threshold at the self.background_suppress percentile
        threshold = np.percentile(band_clahe, self.background_suppress * 100)
        background_mask = band_clahe < threshold           # True = background pixel

        # Smoothly ramp background to black (not a hard cut, preserves gradients)
        suppress_factor = np.where(
            background_mask,
            (band_clahe.astype(np.float32) / max(threshold, 1.0)) * 0.1,  # → near 0
            1.0,
        ).astype(np.float32)
        band_filtered = (band_clahe.astype(np.float32) * suppress_factor).clip(0, 255).astype(np.uint8)

        # ── 4. Reconstruct RGB with bandpass tint ─────────────────────────────
        # Selected channel → full brightness
        # Other two channels → small leak (simulates real filter bleed ~10-20%)
        result = np.zeros_like(arr_u8, dtype=np.float32)
        for i in range(3):
            if i == ch_idx:
                result[:, :, i] = band_filtered.astype(np.float32)
            else:
                # Leaked light from the dominant band + attenuated original channel
                result[:, :, i] = (
                    band_filtered.astype(np.float32) * self.cross_channel_leak
                    + arr_u8[:, :, i].astype(np.float32) * 0.10
                )

        result = result.clip(0, 255).astype(np.uint8)
        return Image.fromarray(result, mode="RGB")


# ─────────────────────────────────────────────────────────────────────────────
# 3. Moiré / Deflectometry Filter Simulation (Grid Distortion over Defects)
# ─────────────────────────────────────────────────────────────────────────────

class MoireDeflectometrySimulation:


    def __init__(
        self,
        p: float = 0.5,
        fringe_frequency: float = 0.08,
        fringe_amplitude: float = 0.12,
        warp_strength: float = 10.0,
        warp_radius: int = 20,
        n_warp_points: int = 6,
    ):
        self.p = p
        self.fringe_frequency = fringe_frequency
        self.fringe_amplitude = fringe_amplitude
        self.warp_strength = warp_strength
        self.warp_radius = warp_radius
        self.n_warp_points = n_warp_points

    def _build_fringe_overlay(self, h: int, w: int, angle_deg: float) -> np.ndarray:
        """
        Build a sinusoidal Moiré fringe pattern at a given angle.
        Returns float32 array (H, W) in [0, 1].
        """
        angle = math.radians(angle_deg)
        yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
        # Project coordinates onto the fringe direction
        projected = xx * math.cos(angle) + yy * math.sin(angle)
        fringe = 0.5 + 0.5 * np.sin(2 * math.pi * self.fringe_frequency * projected)
        return fringe.astype(np.float32)

    def _build_localised_warp_field(
        self, h: int, w: int, edge_mask: np.ndarray
    ) -> tuple:

        dx = np.zeros((h, w), dtype=np.float32)
        dy = np.zeros((h, w), dtype=np.float32)

        # Flatten edge mask for weighted sampling of control points
        flat_mask = edge_mask.ravel()
        total = flat_mask.sum()

        yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)

        for _ in range(self.n_warp_points):
            # Sample a control point weighted by edge probability
            if total > 0 and random.random() < 0.75:
                probs = flat_mask / total
                idx = np.random.choice(h * w, p=probs)
                cy, cx = divmod(idx, w)
            else:
                # Occasionally place a point randomly (avoids degenerate fields)
                cy = random.randint(0, h - 1)
                cx = random.randint(0, w - 1)

            # Random direction and magnitude for this control point
            magnitude  = random.uniform(self.warp_strength * 0.4, self.warp_strength)
            angle      = random.uniform(0, 2 * math.pi)
            ddx        = magnitude * math.cos(angle)
            ddy        = magnitude * math.sin(angle)
            radius     = random.uniform(self.warp_radius * 0.6, self.warp_radius * 1.4)

            # Gaussian bump centred at (cx, cy)
            dist2 = (xx - cx) ** 2 + (yy - cy) ** 2
            bump  = np.exp(-dist2 / (2 * radius ** 2))

            dx += ddx * bump
            dy += ddy * bump

        # Localise: multiply by the blurred edge mask so displacement only
        # exists near detected defect regions
        soft_mask = _gaussian_blur_mask(
            _dilate_mask(edge_mask, radius=self.warp_radius), sigma=self.warp_radius
        )
        dx *= soft_mask
        dy *= soft_mask

        return dx, dy

    def _apply_warp(self, arr_u8: np.ndarray, dx: np.ndarray, dy: np.ndarray) -> np.ndarray:
        """Apply a dense displacement field (dx, dy) to a uint8 RGB image."""
        h, w = arr_u8.shape[:2]
        yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)

        # Target coordinates: for each output pixel, sample from warped source
        map_x = (xx + dx).clip(0, w - 1).astype(np.float32)
        map_y = (yy + dy).clip(0, h - 1).astype(np.float32)

        warped = cv2.remap(
            arr_u8, map_x, map_y,
            interpolation=cv2.INTER_LINEAR,
            borderMode=cv2.BORDER_REFLECT_101
        )
        return warped

    def __call__(self, img: Image.Image) -> Image.Image:
        if random.random() > self.p:
            return img

        arr_u8 = np.asarray(img, dtype=np.uint8).copy()
        h, w   = arr_u8.shape[:2]
        arr_f  = arr_u8.astype(np.float32) / 255.0

        # ── 1. Detect edges for warp localisation ────────────────────────────
        gray_u8   = cv2.cvtColor(arr_u8, cv2.COLOR_RGB2GRAY)
        edge_mask = _detect_edge_mask(gray_u8, low=30, high=100)

        # ── 2. Build and apply localised elastic warp ─────────────────────────
        dx, dy     = self._build_localised_warp_field(h, w, edge_mask)
        warped_u8  = self._apply_warp(arr_u8, dx, dy)
        warped_f   = warped_u8.astype(np.float32) / 255.0

        # ── 3. Overlay Moiré fringe pattern ──────────────────────────────────
        angle  = random.uniform(0, 90)                 # random fringe orientation
        fringe = self._build_fringe_overlay(h, w, angle)    # (H, W) in [0,1]
        fringe3 = fringe[:, :, np.newaxis]             # broadcast to (H, W, 1)

        # Blend fringe: slightly brighten/darken image by fringe pattern
        result = warped_f * (1.0 - self.fringe_amplitude) + warped_f * fringe3 * self.fringe_amplitude
        # Equivalent to: result = warped_f * (1 - amp * (1 - fringe3))
        result = np.clip(result, 0.0, 1.0)

        return _np_to_pil(result)


# ─────────────────────────────────────────────────────────────────────────────
# Public factory: build_augmented_transform()
# ─────────────────────────────────────────────────────────────────────────────

def build_augmented_transform(training: bool = True):

    from torchvision import transforms

    # ── Shared final steps (same for train & inference) ───────────────────────
    normalise = transforms.Compose([
        transforms.Resize((224, 224), interpolation=transforms.InterpolationMode.BICUBIC),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ])

    if not training:
        return normalise

    # ── Training augmentation pipeline ───────────────────────────────────────
    return transforms.Compose([
        # ── Geometry ──────────────────────────────────────────────────────────
        transforms.RandomHorizontalFlip(p=0.5),
        transforms.RandomVerticalFlip(p=0.3),
        transforms.RandomRotation(degrees=15),
        # Slight perspective warp — simulates camera/lens tilt
        transforms.RandomPerspective(distortion_scale=0.2, p=0.3),

        # ── Colour / lighting jitter ──────────────────────────────────────────
        transforms.ColorJitter(brightness=0.3, contrast=0.3, saturation=0.2, hue=0.05),
        transforms.RandomGrayscale(p=0.05),

        # ── Physics-informed optical filter simulations ────────────────────────
        # Applied independently — any combination (or none) can fire on each sample.

        # 1. Polarizing filter: spectral birefringence glow around cracks
        PolarizingFilterSimulation(
            p=0.4,
            hue_shift_range=(0, 360),
            intensity=0.40,
            gabor_freqs=[0.08, 0.15, 0.25],
            edge_dilate_px=14,
        ),

        # 2. Narrow bandpass: dark-field high-contrast crack isolation
        NarrowBandpassFilterSimulation(
            p=0.4,
            channel=None,             # randomly picks red or green each call
            clahe_clip=3.5,
            background_suppress=0.50,
            cross_channel_leak=0.12,
        ),

        # 3. Moiré / deflectometry: elastic grid warp over defect zones
        MoireDeflectometrySimulation(
            p=0.35,
            fringe_frequency=0.08,
            fringe_amplitude=0.12,
            warp_strength=9.0,
            warp_radius=22,
            n_warp_points=6,
        ),

        # ── Final resize + normalise ──────────────────────────────────────────
        normalise,
    ])
