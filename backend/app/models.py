from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class Coordinate(StrictModel):
    x: int = Field(ge=0)
    y: int = Field(ge=0)


class CutRequest(StrictModel):
    board_width: int = Field(ge=2, le=10)
    board_height: int = Field(ge=2, le=10)
    piece_width: int = Field(ge=1, le=5)
    piece_height: int = Field(ge=1, le=5)
    allow_rotation: bool
    defects: list[Coordinate]

    @model_validator(mode="after")
    def validate_relationships(self) -> "CutRequest":
        unrotated_fits = (
            self.piece_width <= self.board_width
            and self.piece_height <= self.board_height
        )
        rotated_fits = (
            self.allow_rotation
            and self.piece_height <= self.board_width
            and self.piece_width <= self.board_height
        )
        if not unrotated_fits and not rotated_fits:
            raise ValueError("target piece dimensions must fit the board")

        for defect in self.defects:
            if defect.x >= self.board_width or defect.y >= self.board_height:
                raise ValueError("defect coordinates must be inside the board")

        unique = {(defect.x, defect.y) for defect in self.defects}
        if len(unique) != len(self.defects):
            raise ValueError("defect coordinates must not repeat")
        return self


class Rectangle(BaseModel):
    x: int
    y: int
    width: int
    height: int


class ProductRectangle(Rectangle):
    rotated: bool


class CutStep(Rectangle):
    cut_id: str
    orientation: Literal["H", "V"]
    coordinate: int
    parent_id: Optional[str]


class TreeNode(BaseModel):
    # Recursive fields are bound after the class is created below.
    id: str
    type: Literal["cut", "leaf"]
    orientation: Optional[Literal["H", "V"]] = None
    coordinate: Optional[int] = None
    role: Optional[Literal["product", "waste"]] = None
    rotated: Optional[bool] = None
    x: int
    y: int
    width: int
    height: int
    first: Optional["TreeNode"] = None
    second: Optional["TreeNode"] = None


TreeNode.model_rebuild()


class Stats(BaseModel):
    product_count: int
    cut_count: int
    waste_area: int


class CutResponse(BaseModel):
    products: list[ProductRectangle]
    waste: list[Rectangle]
    cut_steps: list[CutStep]
    tree: TreeNode
    stats: Stats
