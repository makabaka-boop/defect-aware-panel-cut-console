# 板材直切排样台

一个从零搭建的轻量全栈排样应用：

- **React + SVG**：编辑板材尺寸、目标件尺寸、旋转许可和瑕疵格，并将成品、废料、每一刀的贯穿直切叠画在板格上。
- **FastAPI**：在所有合法直切树中求最优方案。
- **Docker Compose**：一键运行 `web` 与 `api` 两个服务。

## 业务规则

坐标采用整数格左下角原点：

- `x` 向右增加，`y` 向上增加。
- 矩形字段为 `x, y, width, height`。
- 板材宽、高均为 `2..10`。
- 目标件宽、高均为 `1..5`。
- 瑕疵格坐标不得越界、不得重复。
- 目标件可配置是否允许 90° 旋转；若允许，至少原方向或旋转方向之一必须能放入板材。
- 每刀只能沿当前矩形的整数网格线做一次贯穿直切：
  - `H`：水平线，字段 `coordinate` 是全局 `y` 坐标；第一子树为上半块，第二子树为下半块。
  - `V`：竖直线，字段 `coordinate` 是全局 `x` 坐标；第一子树为左半块，第二子树为右半块。
- 叶块只能是：
  - **废料**；或
  - **成品**：尺寸恰好等于目标件某一允许方向，并且不含瑕疵格。

优化顺序为：

1. 成品件数最大；
2. 总切割次数最少；
3. 仍并列时，`H` 优先于 `V`；
4. 同一切向取较小的全局切割坐标；
5. 递归按第一子树先于第二子树比较（先上后下，或先左后右）。

后端使用动态规划枚举每个矩形的叶块、所有 `H` 切法和所有 `V` 切法。因为子矩形带全局位置，比较键中的坐标天然是全局坐标。

## API

### `POST /api/cut`

请求示例：

```json
{
  "board_width": 6,
  "board_height": 4,
  "piece_width": 2,
  "piece_height": 1,
  "allow_rotation": true,
  "defects": [
    {"x": 0, "y": 1},
    {"x": 4, "y": 3}
  ]
}
```

响应包含：

- `products`：成品矩形及是否旋转；
- `waste`：废料叶块；
- `cut_steps`：按前序遍历排列的实际下刀顺序；
- `tree`：确定的递归切割树；
- `stats`：成品数、刀数、废料面积。

切树节点示例：

```json
{
  "id": "n0",
  "type": "cut",
  "orientation": "H",
  "coordinate": 1,
  "x": 0,
  "y": 0,
  "width": 6,
  "height": 4,
  "first": {},
  "second": {}
}
```

越界、重复瑕疵、额外字段、错误类型、尺寸范围错误等均返回 HTTP `422`。

## 本地开发

### 后端

```bash
cd backend
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/uvicorn app.main:app --reload --port 8000
```

运行测试：

```bash
cd backend
.venv/bin/pytest -q
```

测试会对所有小板（宽高 `2..3`）、全部瑕疵格子集、全部目标件宽高和旋转开关，独立枚举完整切树，然后核对动态规划得到的目标值和确定性切树。

### 前端

```bash
cd frontend
npm install
npm run dev
```

Vite 会把 `/api` 代理到 `http://localhost:8000`。

## Docker Compose 运行

```bash
docker compose up --build
```

打开：

- Web：<http://localhost:8080>
- API 健康检查：<http://localhost:8000/health>

## 使用流程

1. 输入板材和目标件尺寸，选择是否允许旋转。
2. 点击 SVG 板格切换瑕疵。
3. 点击“求解并叠画切线”。
4. 绿色矩形为成品，灰色矩形为废料，红线为贯穿直切。
5. 点击下刀顺序胶囊，可高亮当前切割线并显示它所在的当前矩形。
