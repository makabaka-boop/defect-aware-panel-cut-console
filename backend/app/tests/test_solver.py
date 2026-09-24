"""Solver property tests based on exhaustive enumeration of guillotine trees."""

from itertools import product

import pytest

from app.solver import Problem, build_result, solve


def _piece_orientations(piece_width, piece_height, allow_rotation):
    values = [(piece_width, piece_height, False)]
    if allow_rotation and piece_width != piece_height:
        values.append((piece_height, piece_width, True))
    return tuple(values)


def _contains_defect(defects, x, y, width, height):
    return any(
        cell_x in range(x, x + width) and cell_y in range(y, y + height)
        for cell_x, cell_y in defects
    )


def all_optimized_trees(
    board_width,
    board_height,
    piece_width,
    piece_height,
    allow_rotation,
    defects,
    x=0,
    y=0,
    width=None,
    height=None,
):
    """Independent recursive enumerator.

    It generates every full guillotine tree for a rectangle, scores complete
    trees, and yields the same optimal objective/tie tuple as the DP.
    """

    width = board_width if width is None else width
    height = board_height if height is None else height
    orientations = _piece_orientations(
        piece_width, piece_height, allow_rotation
    )

    candidates = []

    has_defect = _contains_defect(defects, x, y, width, height)
    if not has_defect:
        for candidate_w, candidate_h, rotated in orientations:
            if candidate_w == width and candidate_h == height:
                candidates.append(
                    (
                        1,
                        0,
                        (
                            "leaf",
                            "product",
                            x,
                            y,
                            width,
                            height,
                            rotated,
                        ),
                    )
                )

    candidates.append(
        (0, 0, ("leaf", "waste", x, y, width, height, None))
    )

    for coordinate in range(y + 1, y + height):
        upper_height = y + height - coordinate
        for upper, lower in product(
            all_optimized_trees(
                board_width,
                board_height,
                piece_width,
                piece_height,
                allow_rotation,
                defects,
                x,
                coordinate,
                width,
                upper_height,
            ),
            all_optimized_trees(
                board_width,
                board_height,
                piece_width,
                piece_height,
                allow_rotation,
                defects,
                x,
                y,
                width,
                coordinate - y,
            ),
        ):
            products = upper[0] + lower[0]
            cuts = 1 + upper[1] + lower[1]
            key = ("cut", 0, coordinate, upper[2], lower[2])
            candidates.append((products, cuts, key))

    for coordinate in range(x + 1, x + width):
        left_width = coordinate - x
        for left, right in product(
            all_optimized_trees(
                board_width,
                board_height,
                piece_width,
                piece_height,
                allow_rotation,
                defects,
                x,
                y,
                left_width,
                height,
            ),
            all_optimized_trees(
                board_width,
                board_height,
                piece_width,
                piece_height,
                allow_rotation,
                defects,
                coordinate,
                y,
                x + width - coordinate,
                height,
            ),
        ):
            products = left[0] + right[0]
            cuts = 1 + left[1] + right[1]
            key = ("cut", 1, coordinate, left[2], right[2])
            candidates.append((products, cuts, key))

    best = min(candidates, key=lambda item: (-item[0], item[1], item[2]))
    yield best


def canonical(node):
    if node["type"] == "leaf":
        return (
            "leaf",
            node["role"],
            node["x"],
            node["y"],
            node["width"],
            node["height"],
            node["rotated"],
        )
    orientation = 0 if node["orientation"] == "H" else 1
    return (
        "cut",
        orientation,
        node["coordinate"],
        canonical(node["first"]),
        canonical(node["second"]),
    )


def _small_cases():
    cases = []
    for board_width, board_height in product(range(2, 4), repeat=2):
        cells = [
            (x, y)
            for x in range(board_width)
            for y in range(board_height)
        ]
        for defect_mask in range(1 << len(cells)):
            defects = frozenset(
                cell
                for index, cell in enumerate(cells)
                if defect_mask & (1 << index)
            )
            for piece_width, piece_height in product(
                range(1, board_width + 1), range(1, board_height + 1)
            ):
                for allow_rotation in (False, True):
                    cases.append(
                        pytest.param(
                            board_width,
                            board_height,
                            piece_width,
                            piece_height,
                            allow_rotation,
                            defects,
                        )
                    )
    return cases


@pytest.mark.parametrize(
    (
        "board_width",
        "board_height",
        "piece_width",
        "piece_height",
        "allow_rotation",
        "defects",
    ),
    _small_cases(),
)
def test_dp_matches_exhaustive_small_board(
    board_width,
    board_height,
    piece_width,
    piece_height,
    allow_rotation,
    defects,
):
    problem = Problem(
        board_width,
        board_height,
        piece_width,
        piece_height,
        allow_rotation,
        defects,
    )
    tree, cuts = solve(problem)
    expected_products, expected_cuts, expected_key = next(
        all_optimized_trees(
            board_width,
            board_height,
            piece_width,
            piece_height,
            allow_rotation,
            defects,
        )
    )

    actual_products = sum(
        1
        for leaf in _leaves(tree)
        if leaf["role"] == "product"
    )

    assert (actual_products, cuts, canonical(tree)) == (
        expected_products,
        expected_cuts,
        expected_key,
    )


def _leaves(node):
    if node["type"] == "leaf":
        return [node]
    return _leaves(node["first"]) + _leaves(node["second"])


def test_defective_exact_piece_cannot_become_product():
    problem = Problem(
        board_width=2,
        board_height=1 + 1,  # satisfy shared solver while testing concept
        piece_width=2,
        piece_height=1,
        allow_rotation=False,
        defects=frozenset({(0, 0)}),
    )
    result = build_result(problem)
    assert result["stats"]["product_count"] == 1
    product = result["products"][0]
    assert (product["x"], product["y"]) == (0, 1)


def test_tie_break_prefers_horizontal_then_small_coordinate():
    problem = Problem(
        board_width=2,
        board_height=2,
        piece_width=1,
        piece_height=1,
        allow_rotation=False,
        defects=frozenset(),
    )
    result = build_result(problem)
    tree = result["tree"]
    assert tree["orientation"] == "H"
    assert tree["coordinate"] == 1
    assert result["stats"] == {
        "product_count": 4,
        "cut_count": 3,
        "waste_area": 0,
    }


def test_cut_steps_are_preorder_global_lines():
    problem = Problem(
        board_width=3,
        board_height=3,
        piece_width=1,
        piece_height=1,
        allow_rotation=False,
        defects=frozenset(),
    )
    result = build_result(problem)
    assert result["cut_steps"][0] == {
        "cut_id": result["tree"]["id"],
        "orientation": "H",
        "coordinate": 1,
        "x": 0,
        "y": 0,
        "width": 3,
        "height": 3,
        "parent_id": None,
    }
    assert result["stats"]["cut_count"] == len(result["cut_steps"])
