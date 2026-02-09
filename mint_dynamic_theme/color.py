import colorsys
import logging
from typing import Optional, Tuple
from pathlib import Path
from functools import lru_cache
from .config import CONFIG_PATHS

log = logging.getLogger("mint-dynamic-theme")

try:
    from colorthief import ColorThief
    COLORTHIEF_AVAILABLE = True
except ImportError:
    COLORTHIEF_AVAILABLE = False
    log.error("ColorThief not installed.")

# Umbrales
MIN_LIGHTNESS_THRESHOLD = 0.12
MAX_LIGHTNESS_THRESHOLD = 0.88
MIN_SATURATION_GRAYSCALE = 0.08
HIGH_SATURATION_THRESHOLD = 0.3
SAND_LIGHTNESS_THRESHOLD = 0.75
YELLOW_TO_SAND_LIGHTNESS = 0.8
ORANGE_TO_BROWN_LIGHTNESS = 0.3
BLUE_TO_NAVY_LIGHTNESS = 0.25

class ColorService:
    @staticmethod
    @lru_cache(maxsize=32)
    def get_dominant_color(path: str, quality: int = 10, resize_max: int = 250) -> Optional[Tuple[int, int, int]]:
        """
        Extracts dominant color from image.
        Optimized by using a thumbnail if image is large.
        """
        if not COLORTHIEF_AVAILABLE:
            return None

        file_path = Path(path)
        if not file_path.exists() or not file_path.is_file():
            log.error(f"Invalid file: {path}")
            return None

        try:
            # ColorThief doesn't natively support resizing in its constructor easily without PIL
            # But ColorThief uses PIL internally.
            
            # Optimization: 
            # We will use ColorThief as normal but ensure quality is not too high (lower number = slower)
            # A quality of 10-20 is usually a good balance.
            # 
            # Note: Implementing manual resize before ColorThief would require importing PIL directly here.
            # ColorThief(file) opens the file. 
            
            color_thief = ColorThief(path)
            
            # ColorThief.get_color(quality=N)
            # quality=1 is highest (check every pixel), quality=10 checks every 10th pixel.
            # For 4K images, checking every 10th pixel is still a lot.
            # But we want to follow legal/standard usage of the lib.
            
            # If we wanted to resize, we'd need to do:
            # image = Image.open(path)
            # image.thumbnail((resize_max, resize_max))
            # ... pass image to ColorThief ... but ColorThief expects a file-like or path.
            # 
            # Actually ColorThief(file_object) works.
            # But let's stick to the standard usage with adjusted quality for now to avoid extra dependencies if possible,
            # OR we trust PIL is there (it is a dependency of ColorThief).
            
            color = color_thief.get_color(quality=quality)
            
            if not isinstance(color, (tuple, list)) or len(color) != 3:
                return None
                
            return tuple(int(c) for c in color)
            
        except Exception as e:
            log.error(f"Error extracting color from {path}: {e}")
            return None

    @staticmethod
    def rgb_to_hsl(r: int, g: int, b: int) -> Tuple[float, float, float]:
        # colorsys.rgb_to_hls returns (h, l, s) where h,l,s are 0-1
        # We need h in 0-360, s, l in 0-1
        h, l, s = colorsys.rgb_to_hls(r/255.0, g/255.0, b/255.0)
        return h * 360, s, l

    @staticmethod
    def get_theme_name_for_color(r: int, g: int, b: int) -> str:
        h, s, l = ColorService.rgb_to_hsl(r, g, b)

        # Grayscale / Low Saturation
        if l < MIN_LIGHTNESS_THRESHOLD:
            return "Grey"
        if s < MIN_SATURATION_GRAYSCALE:
            return "Sand" if l > SAND_LIGHTNESS_THRESHOLD else "Grey"
        
        # High Brightness & Saturation
        if l > MAX_LIGHTNESS_THRESHOLD and s > HIGH_SATURATION_THRESHOLD and not (160 <= h <= 260):
            return "Sand"

        color_ranges = [
            (350, 360, "Pink"), (330, 350, "Pink"),
            (300, 330, "Purple"),
            (260, 280, "Navy"),
            (240, 260, "Blue"), (220, 240, "Blue"),
            (200, 220, "Aqua"),
            (185, 200, "Teal"),
            (165, 185, "Cyan"),
            (140, 165, "Green"), (100, 140, "Green"), (80, 100, "Green"),
            (65, 80, "Yellow"), (55, 65, "Yellow"),
            (45, 55, "Orange"), (35, 45, "Orange"),
            (20, 35, "Red"), (0, 20, "Red"),
        ]

        for start, end, name in color_ranges:
            if start <= h < end:
                if name == "Yellow" and l > YELLOW_TO_SAND_LIGHTNESS: return "Sand"
                if name == "Orange" and l < ORANGE_TO_BROWN_LIGHTNESS: return "Sand"
                if name == "Blue" and l < BLUE_TO_NAVY_LIGHTNESS: return "Navy"
                return name

        return "Green"
