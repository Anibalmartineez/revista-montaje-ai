import math


def dpi_for_preview(page_mm, max_pixels=10_000_000):
    # Preview ~110 dpi, pero limita a ~10MP
    target_dpi = 110
    w_in = page_mm[0] / 25.4
    h_in = page_mm[1] / 25.4
    est_px = w_in * h_in * target_dpi * target_dpi
    if est_px > max_pixels:
        scale = math.sqrt(max_pixels / est_px)
        target_dpi = max(72, int(target_dpi * scale))
    return target_dpi


def dpi_for_raster_ops(page_mm, max_pixels=12_000_000):
    # Fallback/sangrado ~240 dpi, techo ~12MP
    target_dpi = 240
    w_in = page_mm[0] / 25.4
    h_in = page_mm[1] / 25.4
    est_px = w_in * h_in * target_dpi * target_dpi
    if est_px > max_pixels:
        scale = math.sqrt(max_pixels / est_px)
        target_dpi = max(150, int(target_dpi * scale))
    return target_dpi
