"""Sheet bitmap budget shared only by native V2 preflight and Preview."""

PREVIEW_MAX_PIXELS = 24_000_000


def preview_pixel_size(sheet_size_mm, dpi):
    """Use the renderer's rounded dimensions, not an approximate area in mm²."""
    return tuple(round(float(sheet_size_mm[axis]) * dpi / 25.4)
                 for axis in ('width', 'height'))


def preview_resource_issue(sheet_size_mm, dpi):
    width, height = preview_pixel_size(sheet_size_mm, dpi)
    if width * height > PREVIEW_MAX_PIXELS:
        return (f'La Preview a {dpi} dpi requiere {width} × {height} píxeles '
                f'({width * height:,}); el límite es {PREVIEW_MAX_PIXELS:,}. '
                'Selecciona una resolución menor. Este límite del pliego rasterizado '
                'no impide por sí solo generar el PDF vectorial.')
    return None
