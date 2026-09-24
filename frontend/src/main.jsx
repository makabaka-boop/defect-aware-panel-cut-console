import React, {useMemo, useState} from 'react';
import {createRoot} from 'react-dom/client';
import './styles.css';

const NUMBER_FIELDS = [
  ['boardWidth', '板材宽', 2, 10],
  ['boardHeight', '板材高', 2, 10],
  ['pieceWidth', '目标件宽', 1, 5],
  ['pieceHeight', '目标件高', 1, 5],
];

const SAMPLE = {
  boardWidth: 6,
  boardHeight: 4,
  pieceWidth: 2,
  pieceHeight: 1,
  allowRotation: true,
  defects: new Set(['0,1', '4,3']),
};

function cellKey(x, y) {
  return `${x},${y}`;
}

function App() {
  const [form, setForm] = useState(() => ({
    boardWidth: SAMPLE.boardWidth,
    boardHeight: SAMPLE.boardHeight,
    pieceWidth: SAMPLE.pieceWidth,
    pieceHeight: SAMPLE.pieceHeight,
    allowRotation: SAMPLE.allowRotation,
  }));
  const [defects, setDefects] = useState(() => new Set(SAMPLE.defects));
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [activeStepId, setActiveStepId] = useState(null);

  const cellSize = useMemo(() => {
    return Math.floor(560 / Math.max(form.boardWidth, form.boardHeight));
  }, [form.boardWidth, form.boardHeight]);

  const svgWidth = form.boardWidth * cellSize;
  const svgHeight = form.boardHeight * cellSize;

  const updateNumber = (name, value) => {
    setForm((current) => ({...current, [name]: value}));
    setResult(null);
    setError('');
  };

  const clampNumber = (name, value, min, max) => {
    const normalized = Math.min(max, Math.max(min, value));
    if (name === 'boardWidth' || name === 'boardHeight') {
      resizeBoard(name, normalized);
    } else {
      updateNumber(name, normalized);
    }
  };

  const resizeBoard = (name, value) => {
    const width = name === 'boardWidth' ? value : form.boardWidth;
    const height = name === 'boardHeight' ? value : form.boardHeight;
    setDefects((current) => {
      const next = new Set();
      current.forEach((key) => {
        const [x, y] = key.split(',').map(Number);
        if (x < width && y < height) next.add(key);
      });
      return next;
    });
    updateNumber(name, value);
  };

  const toggleDefect = (x, y) => {
    const key = cellKey(x, y);
    setDefects((current) => {
      const next = new Set(current);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
    setResult(null);
    setError('');
  };

  const resetSample = () => {
    setForm({
      boardWidth: SAMPLE.boardWidth,
      boardHeight: SAMPLE.boardHeight,
      pieceWidth: SAMPLE.pieceWidth,
      pieceHeight: SAMPLE.pieceHeight,
      allowRotation: SAMPLE.allowRotation,
    });
    setDefects(new Set(SAMPLE.defects));
    setResult(null);
    setError('');
    setActiveStepId(null);
  };

  const solve = async () => {
    setLoading(true);
    setError('');
    setResult(null);
    try {
      const payload = {
        board_width: form.boardWidth,
        board_height: form.boardHeight,
        piece_width: form.pieceWidth,
        piece_height: form.pieceHeight,
        allow_rotation: form.allowRotation,
        defects: [...defects].map((key) => {
          const [x, y] = key.split(',').map(Number);
          return {x, y};
        }),
      };
      const response = await fetch('/api/cut', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(payload),
      });
      const data = await response.json();
      if (!response.ok) {
        const message = data.detail
          ? formatValidation(data.detail)
          : '求解失败';
        throw new Error(message);
      }
      setResult(data);
      setActiveStepId(data.cut_steps[0]?.cut_id ?? null);
    } catch (caught) {
      setError(caught.message);
    } finally {
      setLoading(false);
    }
  };

  const activeStep = result?.cut_steps.find(
    (step) => step.cut_id === activeStepId,
  );

  return (
    <main className="page-shell">
      <section className="hero">
        <div>
          <p className="eyebrow">GUILLOTINE CUTTING</p>
          <h1>板材直切排样台</h1>
          <p className="subtitle">
            编辑瑕疵格，计算先最大化成品、再最少下刀的确定性切割树。
          </p>
        </div>
        <div className="sample-action">
          <button type="button" onClick={resetSample}>载入样例</button>
        </div>
      </section>

      <section className="workspace">
        <aside className="panel controls">
          <h2>1. 编辑参数</h2>
          <div className="number-grid">
            {NUMBER_FIELDS.map(([name, label, min, max]) => (
              <label key={name}>
                {label}
                <input
                  name={name}
                  type="number"
                  min={min}
                  max={max}
                  value={form[name]}
                  onChange={(event) => updateNumber(name, Number(event.target.value))}
                  onBlur={(event) => {
                    const value = Number(event.target.value);
                    if (Number.isFinite(value)) {
                      clampNumber(name, value, min, max);
                    } else {
                      clampNumber(name, min, min, max);
                    }
                  }}
                />
              </label>
            ))}
          </div>
          <label className="check-row">
            <input
              type="checkbox"
              checked={form.allowRotation}
              onChange={(event) => {
                setForm((current) => ({
                  ...current,
                  allowRotation: event.target.checked,
                }));
                setResult(null);
              }}
            />
            允许目标件 90° 旋转
          </label>

          <div className="target-preview-block">
            <h3>目标件</h3>
            <TargetPreview
              width={form.pieceWidth}
              height={form.pieceHeight}
            />
            <p>
              {form.pieceWidth} × {form.pieceHeight}
              {form.allowRotation ? '，可旋转' : '，不可旋转'}
            </p>
          </div>

          <h2>2. 点击格点</h2>
          <p className="hint">
            点击板材格子可切换瑕疵。瑕疵格不会进入成品。
          </p>
          <div className="legend">
            <span><i className="normal" />普通格</span>
            <span><i className="defect" />瑕疵格</span>
          </div>

          <button
            type="button"
            className="primary"
            disabled={loading}
            onClick={solve}
          >
            {loading ? '计算中…' : '求解并叠画切线'}
          </button>
          {error && <div className="error-box">{error}</div>}
        </aside>

        <section className="panel drawing-panel">
          <div className="drawing-heading">
            <h2>板格与切割方案</h2>
            {result && (
              <div className="stats">
                <strong>{result.stats.product_count}</strong> 件成品
                <strong>{result.stats.cut_count}</strong> 刀
                <strong>{result.stats.waste_area}</strong> 格废料
              </div>
            )}
          </div>

          <BoardSvg
            width={form.boardWidth}
            height={form.boardHeight}
            cellSize={cellSize}
            svgWidth={svgWidth}
            svgHeight={svgHeight}
            defects={defects}
            result={result}
            activeStep={activeStep}
            onCellClick={toggleDefect}
          />

          {result && (
            <CutSteps
              steps={result.cut_steps}
              activeStepId={activeStepId}
              onActivate={setActiveStepId}
            />
          )}
        </section>
      </section>
    </main>
  );
}

function BoardSvg({
  width,
  height,
  cellSize,
  svgWidth,
  svgHeight,
  defects,
  result,
  activeStep,
  onCellClick,
}) {
  const yFor = (gridY, itemHeight = 0) => (height - gridY - itemHeight) * cellSize;

  return (
    <div className="svg-wrap">
      <svg
        width={svgWidth}
        height={svgHeight}
        viewBox={`0 0 ${svgWidth} ${svgHeight}`}
        role="img"
        aria-label="板材网格和切割方案"
      >
        <rect x={0} y={0} width={svgWidth} height={svgHeight} className="board-bg" />

        {Array.from({length: width}, (_, x) =>
          Array.from({length: height}, (_, y) => {
            const defective = defects.has(cellKey(x, y));
            return (
              <g
                key={cellKey(x, y)}
                className="cell"
                role="button"
                tabIndex={0}
                onClick={() => onCellClick(x, y)}
                onKeyDown={(event) => {
                  if (event.key === 'Enter' || event.key === ' ') onCellClick(x, y);
                }}
              >
                <rect
                  x={x * cellSize + 1}
                  y={yFor(y) + 1}
                  width={cellSize - 2}
                  height={cellSize - 2}
                  rx={3}
                  className={defective ? 'defect-cell' : 'normal-cell'}
                />
                {defective && (
                  <text
                    x={x * cellSize + cellSize / 2}
                    y={yFor(y) + cellSize / 2 + 5}
                    textAnchor="middle"
                    className="defect-x"
                  >
                    ×
                  </text>
                )}
              </g>
            );
          }),
        )}

        {Array.from({length: width + 1}, (_, x) => (
          <line
            key={`grid-v-${x}`}
            x1={x * cellSize}
            y1={0}
            x2={x * cellSize}
            y2={svgHeight}
            className="grid-line"
          />
        ))}
        {Array.from({length: height + 1}, (_, y) => (
          <line
            key={`grid-h-${y}`}
            x1={0}
            y1={y * cellSize}
            x2={svgWidth}
            y2={y * cellSize}
            className="grid-line"
          />
        ))}

        {result?.waste.map((part) => (
          <rect
            key={`waste-${part.x}-${part.y}`}
            x={part.x * cellSize}
            y={yFor(part.y, part.height)}
            width={part.width * cellSize}
            height={part.height * cellSize}
            className="waste-overlay"
          />
        ))}

        {result?.products.map((part, index) => (
          <g key={`product-${part.x}-${part.y}`}>
            <rect
              x={part.x * cellSize + 3}
              y={yFor(part.y, part.height) + 3}
              width={part.width * cellSize - 6}
              height={part.height * cellSize - 6}
              rx={5}
              className="product-overlay"
            />
            <text
              x={(part.x + part.width / 2) * cellSize}
              y={yFor(part.y, part.height) + part.height * cellSize / 2 + 5}
              textAnchor="middle"
              className="product-label"
            >
              {index + 1}
            </text>
          </g>
        ))}

        {activeStep && (
          <rect
            x={activeStep.x * cellSize}
            y={yFor(activeStep.y, activeStep.height)}
            width={activeStep.width * cellSize}
            height={activeStep.height * cellSize}
            className="active-rectangle"
          />
        )}

        {result?.cut_steps.map((step) => {
          const active = activeStep?.cut_id === step.cut_id;
          const common = {
            className: active ? 'cut-line active' : 'cut-line',
            key: step.cut_id,
          };
          if (step.orientation === 'H') {
            const y = (height - step.coordinate) * cellSize;
            return (
              <line
                {...common}
                x1={step.x * cellSize}
                y1={y}
                x2={(step.x + step.width) * cellSize}
                y2={y}
              />
            );
          }
          const x = step.coordinate * cellSize;
          return (
            <line
              {...common}
              x1={x}
              y1={yFor(step.y, step.height)}
              x2={x}
              y2={yFor(step.y)}
            />
          );
        })}

      </svg>
    </div>
  );
}

function TargetPreview({width, height}) {
  const size = 18;
  return (
    <svg
      width={Math.max(width * size, 40)}
      height={Math.max(height * size, 40)}
      viewBox={`0 0 ${Math.max(width * size, 40)} ${Math.max(height * size, 40)}`}
      className="target-svg"
    >
      <rect
        x={1}
        y={1}
        width={width * size - 2}
        height={height * size - 2}
        rx={4}
      />
    </svg>
  );
}

function CutSteps({steps, activeStepId, onActivate}) {
  return (
    <div className="steps-block">
      <h3>按顺序下刀</h3>
      <ol className="steps-list">
        {steps.map((step, index) => (
          <li key={step.cut_id}>
            <button
              type="button"
              className={step.cut_id === activeStepId ? 'selected' : ''}
              onClick={() => onActivate(step.cut_id)}
            >
              <span>{index + 1}</span>
              {step.orientation === 'H' ? '水平切' : '竖直切'}
              <strong>
                {step.orientation === 'H'
                  ? `y = ${step.coordinate}`
                  : `x = ${step.coordinate}`}
              </strong>
            </button>
          </li>
        ))}
      </ol>
    </div>
  );
}

function formatValidation(detail) {
  if (typeof detail === 'string') return detail;
  if (!Array.isArray(detail)) return '输入未通过校验（422）';
  return detail
    .map((item) => {
      const location = item.loc?.slice(1).join('.') || '请求';
      return `${location}：${item.msg}`;
    })
    .join('；');
}

createRoot(document.getElementById('root')).render(<App />);
