"""Deterministic bounded rectangular Repeat packing, owned entirely by V2.

Free rectangles may overlap each other, never occupied footprints. Subtract each
occupied rectangle expanded by the requested X/Y gap; new pieces are not expanded
again. Sheet edges receive no extra gap. Up to four stable orderings within
priority bands, each with two orientation/position scoring variants, search shared
free space. Preferences select candidate positions, not hard zones. This heuristic
never claims geometric impossibility except oversize pieces.
"""
from __future__ import annotations

from dataclasses import dataclass
from .geometry import Bounds, Size, oriented_size, validate_non_negative

ENGINE_VERSION = "v2-repeat-1.0.0"
EPS = 1e-9
MAX_ITEMS = 128
MAX_PLACEMENTS = 2000
MAX_OBSTACLES = 2000
MAX_FREE_RECTANGLES = 1024
MAX_EFFORT = 1_000_000


@dataclass(frozen=True)
class Piece:
    work_id: str
    size: Size  # unrotated productive footprint, already includes bleed
    quantity: int
    rotations: tuple[int, ...]
    priority: float = 0
    zone: str = "auto"
    flow: str = "auto"


@dataclass(frozen=True)
class Placement:
    work_id: str
    bounds: Bounds
    rotation: int


@dataclass(frozen=True)
class PackingProblem:
    area: Bounds
    pieces: tuple[Piece, ...]
    gap_x: float
    gap_y: float
    obstacles: tuple[Bounds, ...] = ()
    fill: bool = False
    respect_priority: bool = True


@dataclass(frozen=True)
class PackingResult:
    placements: tuple[Placement, ...]
    oversized: tuple[str, ...] = ()
    limited: bool = False
    effort: int = 0


class _Limit(Exception):
    pass


class _Budget:
    def __init__(self, maximum):
        self.maximum = maximum
        self.used = 0

    def tick(self):
        self.used += 1
        if self.used > self.maximum:
            raise _Limit


def separated(a: Bounds, b: Bounds, gap_x: float, gap_y: float) -> bool:
    """At least one separating axis must have its full requested gap."""
    return (a.right + gap_x <= b.left + EPS or b.right + gap_x <= a.left + EPS
            or a.top + gap_y <= b.bottom + EPS or b.top + gap_y <= a.bottom + EPS)


def _contains(a, b):
    return (a.left <= b.left + EPS and a.right >= b.right - EPS
            and a.bottom <= b.bottom + EPS and a.top >= b.top - EPS)


def _subtract(free, occupied, gx, gy, budget):
    cut = Bounds(occupied.left-gx, occupied.right+gx, occupied.bottom-gy, occupied.top+gy)
    split = []
    for r in free:
        budget.tick()
        if separated(r, cut, 0, 0):
            split.append(r)
            continue
        if cut.left > r.left + EPS:
            split.append(Bounds(r.left, min(cut.left,r.right),r.bottom,r.top))
        if cut.right < r.right - EPS:
            split.append(Bounds(max(cut.right,r.left),r.right,r.bottom,r.top))
        if cut.bottom > r.bottom + EPS:
            split.append(Bounds(r.left,r.right,r.bottom,min(cut.bottom,r.top)))
        if cut.top < r.top - EPS:
            split.append(Bounds(r.left,r.right,max(cut.top,r.bottom),r.top))
    # Larger rectangles first: removing contained rectangles is safe and stable.
    unique = sorted(set(split), key=lambda r:(-r.width*r.height,r.bottom,r.left,r.top,r.right))
    kept = []
    for r in unique:
        for other in kept:
            budget.tick()
            if _contains(other,r):
                break
        else:
            kept.append(r)
            if len(kept) > MAX_FREE_RECTANGLES:
                raise _Limit
    return kept


def _candidate(piece, free, area, budget, prefer_orientation=False):
    best = None
    best_score = None
    for rotation in sorted(piece.rotations):
        size = oriented_size(piece.size,rotation)
        for r in free:
            budget.tick()
            if size.width > r.width+EPS or size.height > r.height+EPS:
                continue
            xs = [r.left, max(r.left,r.right-size.width)]
            ys = [r.bottom, max(r.bottom,r.top-size.height)]
            if piece.zone == 'center':
                xs.append(max(r.left,min(r.right-size.width,area.center.x-size.width/2)))
                ys.append(max(r.bottom,min(r.top-size.height,area.center.y-size.height/2)))
            for x in sorted(set(xs)):
                for y in sorted(set(ys)):
                    budget.tick()
                    b = Bounds(x,x+size.width,y,y+size.height)
                    if piece.zone == 'top': pos=(-b.top,b.left)
                    elif piece.zone == 'bottom': pos=(b.bottom,b.left)
                    elif piece.zone == 'left': pos=(b.left,b.bottom)
                    elif piece.zone == 'right': pos=(-b.right,b.bottom)
                    elif piece.zone == 'center': pos=((b.center.x-area.center.x)**2+(b.center.y-area.center.y)**2,b.bottom)
                    elif piece.flow == 'vertical': pos=(b.left,b.bottom)
                    else: pos=(b.bottom,b.left)
                    slack=(r.width-size.width,r.height-size.height)
                    orientation = (rotation,) if prefer_orientation else ()
                    score=(*orientation,*pos,min(slack),max(slack),rotation,b.left,b.bottom)
                    if best_score is None or score < best_score:
                        best_score=score
                        best=Placement(piece.work_id,b,rotation)
    return best


def pack(problem: PackingProblem, *, max_effort: int = MAX_EFFORT) -> PackingResult:
    """Pure bounded search; counts stay compact even for enormous requests."""
    p = problem
    validate_non_negative(p.gap_x,'gap_x'); validate_non_negative(p.gap_y,'gap_y')
    if p.area.width <= 0 or p.area.height <= 0:
        raise ValueError('El área imprimible debe ser positiva.')
    if len(p.pieces)>MAX_ITEMS or len(p.obstacles)>MAX_OBSTACLES:
        return PackingResult((),limited=True)
    if len({i.work_id for i in p.pieces}) != len(p.pieces):
        raise ValueError('Los trabajos deben tener identidades únicas.')
    for i in p.pieces:
        if isinstance(i.quantity,bool) or not isinstance(i.quantity,int) or i.quantity<1:
            raise ValueError('La cantidad debe ser un entero positivo.')
        if not i.rotations or any(r not in (0,90,180,270) for r in i.rotations):
            raise ValueError('Giros no cardinales o ausentes.')
        if i.zone not in {'auto','fill','top','bottom','left','right','center'} or i.flow not in {'auto','horizontal','vertical'}:
            raise ValueError('Preferencia de distribución no soportada.')
    if sum(i.quantity for i in p.pieces)>MAX_PLACEMENTS:
        return PackingResult((),limited=True)
    oversized=tuple(i.work_id for i in p.pieces if not any(
        oriented_size(i.size,r).width<=p.area.width+EPS and oriented_size(i.size,r).height<=p.area.height+EPS
        for r in i.rotations))
    budget=_Budget(max_effort)
    base=[p.area]
    try:
        for obstacle in p.obstacles:
            base=_subtract(base,obstacle,p.gap_x,p.gap_y,budget)
    except _Limit:
        return PackingResult((),oversized,True,budget.used)
    base_order=sorted(p.pieces,key=lambda i:((i.priority if p.respect_priority else 0),i.zone=='fill',i.work_id))
    orders=[]
    for metric in (lambda i:0,lambda i:-i.size.width*i.size.height,
                   lambda i:-max(i.size.width,i.size.height),lambda i:-min(i.size.width,i.size.height)):
        order=sorted(base_order,key=lambda i:((i.priority if p.respect_priority else 0),i.zone=='fill',metric(i)))
        if order not in orders: orders.append(order)
    best=[]; best_free=base; best_score=None; limited=False
    # Compare flow-first and stable-orientation packing. The latter avoids
    # needless mixed rotations when a compact uniform arrangement also fits.
    for order, prefer_orientation in [(order, orientation) for order in orders for orientation in (False, True)]:
        placements=[]; free=list(base); counts={i.work_id:0 for i in p.pieces}
        try:
            for i in order:
                if i.work_id in oversized: continue
                for _ in range(i.quantity):
                    placed=_candidate(i,free,p.area,budget,prefer_orientation)
                    if placed is None: break
                    # Commit free-space and placement together; budget exhaustion
                    # must not leave a reusable free rectangle covering this piece.
                    updated=_subtract(free,placed.bounds,p.gap_x,p.gap_y,budget)
                    free=updated; placements.append(placed); counts[i.work_id]+=1
        except _Limit:
            limited=True
        count_priority=tuple(sum(counts[i.work_id] for i in base_order if i.priority==priority)
                             for priority in sorted({i.priority for i in base_order})) if p.respect_priority else ()
        envelope = ((max(q.bounds.right for q in placements)-min(q.bounds.left for q in placements))
                    * (max(q.bounds.top for q in placements)-min(q.bounds.bottom for q in placements))) if placements else 0
        score=(len(placements)==sum(i.quantity for i in p.pieces),*count_priority,len(placements),
               sum(q.bounds.width*q.bounds.height for q in placements),-envelope)
        if best_score is None or score>best_score:
            best=placements; best_free=free; best_score=score
        if limited: break
    # Demand first. No extras while ANY work is missing, even with allow_partial.
    if p.fill and not limited and len(best)==sum(i.quantity for i in p.pieces):
        try:
            while len(best)<MAX_PLACEMENTS:
                for i in base_order:
                    placed=_candidate(i,best_free,p.area,budget)
                    if placed is not None: break
                else: break
                updated=_subtract(best_free,placed.bounds,p.gap_x,p.gap_y,budget)
                best_free=updated; best.append(placed)
            else: limited=True
        except _Limit:
            limited=True
    return PackingResult(tuple(best),oversized,limited,budget.used)
