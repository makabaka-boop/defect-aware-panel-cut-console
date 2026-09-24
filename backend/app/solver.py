"""Optimal guillotine cutting solver.

Grid cells are addressed by their lower-left corner in a Cartesian coordinate
system.  A rectangle starts at ``(x, y)`` and spans ``width`` cells to the
right and ``height`` cells upward.
"""

from dataclasses import dataclass
from typing import Literal, Optional, TypedDict


class CutNode(TypedDict):
    id: str
    type: Literal["cut"]
    orientation: Literal["H", "V"]
    coordinate: int
    x: int
    y: int
    width: int
    height: int
    first: "TreeNode"
    second: "TreeNode"


class LeafNode(TypedDict):
    id: str
    type: Literal["leaf"]
    role: Literal["product", "waste"]
    x: int
    y: int
    width: int
    height: int
    rotated: Optional[bool]


TreeNode = CutNode | LeafNode


@dataclass(frozen=True)
class Problem:
    board_width: int
    board_height: int
    piece_width: int
    piece_height: int
    allow_rotation: bool
    defects: frozenset[tuple[int, int]]

    @property
    def orientations(self) -> tuple[tuple[int, int, bool], ...]:
        values = [(self.piece_width, self.piece_height, False)]
        if self.allow_rotation and (
            self.piece_width != self.piece_height
        ):
            values.append((self.piece_height, self.piece_width, True))
        return tuple(values)


def _piece_matches(
    problem: Problem, width: int, height: int
) -> tuple[bool, bool] | None:
    """Return ``(is_product, rotated)`` for a defect-free product candidate."""

    for piece_width, piece_height, rotated in problem.orientations:
        if width == piece_width and height == piece_height:
            return True, rotated
    return None


def _prefetch_defects(problem: Problem) -> list[list[bool]]:
    return [
        [
            (x, y) in problem.defects
            for y in range(problem.board_height)
        ]
        for x in range(problem.board_width)
    ]


def _has_defect(
    defect_grid: list[list[bool]], x: int, y: int, width: int, height: int
) -> bool:
    for cell_x in range(x, x + width):
        for cell_y in range(y, y + height):
            if defect_grid[cell_x][cell_y]:
                return True
    return False


def _key(node: TreeNode) -> tuple:
    """Canonical key implementing the required global tie-breaker."""

    if node["type"] == "leaf":
        # Product leaves outrank waste leaves after numeric optimization keys
        # are already equal.  This only has to be deterministic and consistent.
        return (
            "leaf",
            node["role"],
            node["x"],
            node["y"],
            node["width"],
            node["height"],
            node["rotated"],
        )

    # H is compared before V, followed by smaller global cut coordinate and
    # then first/second subtree (upper before lower, left before right).
    orientation_order = 0 if node["orientation"] == "H" else 1
    return (
        "cut",
        orientation_order,
        node["coordinate"],
        _key(node["first"]),
        _key(node["second"]),
    )


def _leaf(
    role: Literal["product", "waste"],
    x: int,
    y: int,
    width: int,
    height: int,
    rotated: Optional[bool],
) -> LeafNode:
    return {
        "id": "",
        "type": "leaf",
        "role": role,
        "x": x,
        "y": y,
        "height": height,
        "width": width,
        "rotated": rotated,
    }


def solve(problem: Problem) -> tuple[TreeNode, int]:
    """Return the optimal cut tree and total number of cuts.

    Every rectangle is optimized independently by:

    1. maximum number of products;
    2. minimum number of cuts;
    3. H before V, lower global cut coordinate first, and recursively the
       first child before the second.
    """

    defect_grid = _prefetch_defects(problem)
    memo: dict[tuple[int, int, int, int], tuple[TreeNode, int, int]] = {}

    def best_for(
        x: int, y: int, width: int, height: int
    ) -> tuple[TreeNode, int, int]:
        state = (x, y, width, height)
        if state in memo:
            return memo[state]

        contains_defect = _has_defect(defect_grid, x, y, width, height)
        candidates: list[tuple[int, int, tuple, TreeNode]] = []

        # A leaf may be waste, or a product only when it is exactly one target
        # piece and contains no defective cell.
        if not contains_defect:
            match = _piece_matches(problem, width, height)
            if match is not None:
                _, rotated = match
                product = _leaf("product", x, y, width, height, rotated)
                candidates.append((1, 0, _key(product), product))

        waste = _leaf("waste", x, y, width, height, None)
        candidates.append((0, 0, _key(waste), waste))

        # Horizontal cuts: upper/first rectangle then lower/second rectangle.
        for coordinate in range(y + 1, y + height):
            upper_height = y + height - coordinate
            upper, upper_products, upper_cuts = best_for(
                x, coordinate, width, upper_height
            )
            lower, lower_products, lower_cuts = best_for(x, y, width, coordinate - y)
            node: CutNode = {
                "id": "",
                "type": "cut",
                "orientation": "H",
                "coordinate": coordinate,
                "x": x,
                "y": y,
                "width": width,
                "height": height,
                "first": upper,
                "second": lower,
            }
            candidates.append(
                (
                    upper_products + lower_products,
                    1 + upper_cuts + lower_cuts,
                    _key(node),
                    node,
                )
            )

        # Vertical cuts: left/first rectangle then right/second rectangle.
        for coordinate in range(x + 1, x + width):
            left_width = coordinate - x
            left, left_products, left_cuts = best_for(x, y, left_width, height)
            right, right_products, right_cuts = best_for(
                coordinate, y, x + width - coordinate, height
            )
            node = {
                "id": "",
                "type": "cut",
                "orientation": "V",
                "coordinate": coordinate,
                "x": x,
                "y": y,
                "width": width,
                "height": height,
                "first": left,
                "second": right,
            }
            candidates.append(
                (
                    left_products + right_products,
                    1 + left_cuts + right_cuts,
                    _key(node),
                    node,
                )
            )

        # Tuple order is products descending, cuts ascending, canonical key
        # ascending.  Negating products makes ordinary min selection work.
        products, cuts, _, best = min(
            candidates, key=lambda item: (-item[0], item[1], item[2])
        )
        memo[state] = (best, products, cuts)
        return memo[state]

    tree, _, cuts = best_for(0, 0, problem.board_width, problem.board_height)
    return tree, cuts


def enumerate_leaves(tree: TreeNode) -> list[LeafNode]:
    if tree["type"] == "leaf":
        return [tree]
    return enumerate_leaves(tree["first"]) + enumerate_leaves(tree["second"])


def _assign_ids(tree: TreeNode, prefix: str = "n") -> TreeNode:
    counter = 0

    def visit(node: TreeNode) -> TreeNode:
        nonlocal counter
        current_id = f"{prefix}{counter}"
        counter += 1
        if node["type"] == "leaf":
            return {**node, "id": current_id}
        return {
            **node,
            "id": current_id,
            "first": visit(node["first"]),
            "second": visit(node["second"]),
        }

    return visit(tree)


def build_result(problem: Problem) -> dict:
    tree, cuts = solve(problem)
    tree = _assign_ids(tree)
    leaves = enumerate_leaves(tree)
    products = [
        {
            "x": leaf["x"],
            "y": leaf["y"],
            "width": leaf["width"],
            "height": leaf["height"],
            "rotated": bool(leaf["rotated"]),
        }
        for leaf in leaves
        if leaf["role"] == "product"
    ]
    waste = [
        {
            "x": leaf["x"],
            "y": leaf["y"],
            "width": leaf["width"],
            "height": leaf["height"],
        }
        for leaf in leaves
        if leaf["role"] == "waste"
    ]

    cut_steps: list[dict] = []

    def emit_steps(node: TreeNode, parent_id: str | None = None) -> None:
        if node["type"] == "leaf":
            return
        step = {
            "cut_id": node["id"],
            "orientation": node["orientation"],
            "coordinate": node["coordinate"],
            "x": node["x"],
            "y": node["y"],
            "width": node["width"],
            "height": node["height"],
            "parent_id": parent_id,
        }
        # Preorder is the order in which the currently available rectangle can
        # actually be cut: first create children, then process them in order.
        cut_steps.append(step)
        emit_steps(node["first"], node["id"])
        emit_steps(node["second"], node["id"])

    emit_steps(tree)

    return {
        "products": products,
        "waste": waste,
        "cut_steps": cut_steps,
        "tree": tree,
        "stats": {
            "product_count": len(products),
            "cut_count": cuts,
            "waste_area": sum(part["width"] * part["height"] for part in waste),
        },
    }
