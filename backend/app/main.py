from fastapi import FastAPI

from .models import CutRequest, CutResponse
from .solver import Problem, build_result

app = FastAPI(
    title="Guillotine Cutting Optimization API",
    version="1.0.0",
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/cut", response_model=CutResponse)
def optimize_cut(request: CutRequest) -> dict:
    problem = Problem(
        board_width=request.board_width,
        board_height=request.board_height,
        piece_width=request.piece_width,
        piece_height=request.piece_height,
        allow_rotation=request.allow_rotation,
        defects=frozenset((item.x, item.y) for item in request.defects),
    )
    return build_result(problem)
