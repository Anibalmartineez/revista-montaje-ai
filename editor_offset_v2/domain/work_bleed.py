"""Work-owned bleed authorization and explicit physical box coverage for V2."""

WORK_BLEED_STRATEGIES = frozenset({"source_only", "mirror_if_missing"})


def allows_mirror(work, legacy_permission=False):
    """Absent strategy preserves the old request-scoped behavior; never migrates it."""
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
    return (bleed == 0 or (clip == "bleed_box" and boxes.get("bleed") is not None
            and boxes.get("media") is not None and boxes.get(selected) is not None
            and _declared_margin(boxes, selected) + 0.001 >= bleed))
