"""Work-owned bleed authorization and explicit physical box coverage for V2."""

WORK_BLEED_STRATEGIES = frozenset({"source_only", "mirror_if_missing"})


def allows_mirror(work, legacy_permission=False):
    """A positive work bleed is the operator's instruction to make it if needed."""
    bleed = (work or {}).get("bleed_mm")
    if isinstance(bleed, (int, float)) and not isinstance(bleed, bool) and bleed > 0:
        return True
    strategy = (work or {}).get("bleed_strategy")
    if strategy is None:
        return bool(legacy_permission)
    return strategy == "mirror_if_missing"


def _declared_margin(boxes, selected):
    trim = boxes.get(selected)
    if not trim or not boxes.get("bleed") or not boxes.get("media"):
        return 0.0
    return min(
        margin
        for outer in (boxes["media"], boxes["bleed"])
        for margin in (
            trim["x"] - outer["x"], trim["y"] - outer["y"],
            outer["x"] + outer["width"] - trim["x"] - trim["width"],
            outer["y"] + outer["height"] - trim["y"] - trim["height"],
        )
    )


def available_bleed(boxes, selected):
    """Millimetres explicitly covered on all edges, not a claim about artwork ink."""
    return max(0.0, _declared_margin(boxes, selected))


def source_covers_bleed(boxes, selected, bleed, clip="bleed_box"):
    # PDF boxes are often rounded to whole points before inspection. That can
    # make an intended 3 mm bleed appear a few microns short after conversion
    # to millimetres. Match the native preflight tolerance while still
    # rejecting meaningful gaps in declared coverage.
    box_rounding_tolerance_mm = 0.01
    return (bleed == 0 or (clip == "bleed_box" and boxes.get("bleed") is not None
            and boxes.get("media") is not None and boxes.get(selected) is not None
            and _declared_margin(boxes, selected) + box_rounding_tolerance_mm >= bleed))
