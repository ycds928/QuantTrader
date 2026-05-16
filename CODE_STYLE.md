# CODE_STYLE.md — QuantFlow 代码风格与规范

## 通用规范

### 命名

| 场景 | 风格 | 示例 |
|------|------|------|
| 文件名（前端） | kebab-case | `strategy-engine/` / `use-websocket.ts` |
| 文件名（后端） | snake_case | `strategy_engine/` / `router.py` |
| 变量/函数 | camelCase（前端）/ snake_case（后端） | `fetchSymbols` / `get_symbols` |
| 类/接口/类型 | PascalCase | `Strategy` / `ApiResponse` |
| 常量 | UPPER_SNAKE_CASE | `MAX_RETRIES` / `DEFAULT_PAGE_SIZE` |
| CSS 变量 | kebab-case | `--color-primary` / `--shadow-card` |
| 数据库表名 | snake_case 复数 | `strategies` / `orders` |

### 提交信息

遵循 [Conventional Commits](https://www.conventionalcommits.org/)：

```
<type>(<scope>): <description>

type: feat | fix | refactor | docs | style | test | chore
scope: 模块名（api-data / account / strategy / execution / review / replay / common）
```

示例：
```
feat(strategy): 添加策略创建接口
fix(api-data): 修复K线数据时区问题
refactor(common): 重构请求拦截器错误处理
```

### 禁止事项

- 禁止提交 `.env` 文件、IDE 配置、`node_modules/`、`__pycache__/`
- 禁止硬编码敏感信息（密钥、密码、token），一律走 `.env`
- 禁止直接修改公共模块，需提 PR

---

## 前端规范

### TypeScript

- **strict 模式**：`tsconfig.json` 开启 `"strict": true`
- **禁止 `any`**：所有参数和返回值必须标注类型，如无法确定用 `unknown` 并做类型守卫
- **路径别名**：使用 `@/` 代替相对路径，`@/` 映射 `src/`
  ```typescript
  // ✅
  import { cn } from '@/common/utils'
  import type { ApiResponse } from '@/common/types'

  // ❌
  import { cn } from '../../common/utils'
  ```
- **类型先行**：先定义 interface/type，再写组件或函数

### React 组件

- **函数组件 + Hook**：禁止 class 组件
- **Props 类型**：使用独立 interface，不内联
  ```typescript
  interface MetricCardProps {
    label: string
    value: string
    trend?: 'up' | 'down'
  }

  export function MetricCard({ label, value, trend }: MetricCardProps) { ... }
  ```
- **导出方式**：使用命名导出，禁止默认导出
  ```typescript
  // ✅
  export function Dashboard() { ... }

  // ❌
  export default function Dashboard() { ... }
  ```
- **懒加载**：所有模块页面在 `routes.ts` 中用 `lazy()` 导入
- **useEffect 依赖**：必须完整声明依赖数组，禁止遗漏

### 样式

- **只使用 CSS 变量 class**：`bg-background`、`text-on-surface`、`bg-surface-container-high`
- **禁止硬编码颜色**：严禁 `#000`、`rgb(...)`、`bg-blue-500`、`text-gray-300` 等
- **禁止硬编码圆角**：严禁 `rounded-[8px]`，使用 `rounded-md` / `rounded-lg` 等
- **class 合并**：使用 `cn()` 函数（clsx + tailwind-merge）
  ```typescript
  import { cn } from '@/common/utils'

  <div className={cn('bg-surface-container-high rounded-lg p-4', isActive && 'ring-2 ring-primary/30')} />
  ```

### 涨跌色（中国惯例）

- **涨（红）**：`text-up`（#ef4444），正数前缀 `+`
- **跌（绿）**：`text-down`（#22c55e），负数前缀 `-`
- 数字使用 `font-mono-num` class（JetBrains Mono + tabular-nums）

```typescript
<span className={cn('font-mono-num', pnl >= 0 ? 'text-up' : 'text-down')}>
  {formatPnL(pnl)}
</span>
```

### API 层

- 每个模块的 `api/` 目录下定义请求函数，不直接在组件中调用 `axios`
- 使用 `@/common/utils/request`（已配 baseURL 和拦截器）
- 返回类型使用 `ApiResponse<T>` 泛型

```typescript
// src/strategy-engine/api/strategy.ts
import request from '@/common/utils/request'
import type { ApiResponse, PaginatedResponse } from '@/common/types'
import type { Strategy } from '../types/strategy'

export function getStrategyList(page = 1, pageSize = 20) {
  return request.get<ApiResponse<PaginatedResponse<Strategy>>>('/strategy/list', {
    params: { page, page_size: pageSize },
  })
}
```

---

## 后端规范

### Python

- **版本**：3.12+
- **async/await 优先**：所有数据库操作和外部调用必须异步
- **类型注解必须**：所有函数参数和返回值必须标注类型
  ```python
  async def get_symbols(db: AsyncSession = Depends(get_db)) -> dict:
      ...
  ```
- **import 顺序**：标准库 → 第三方 → 本地，各组间空一行
  ```python
  import os
  from typing import Optional

  from fastapi import APIRouter, Depends
  from sqlalchemy import select

  from common.database import get_db
  from .models import Symbol
  from .schemas import SymbolResponse
  ```

### API 路由

- 每个模块一个 `APIRouter`，在 `router.py` 中定义
- 路由前缀：`/api/{module_name}/...`
- 使用 `tags` 参数分组（Swagger UI 展示）
  ```python
  router = APIRouter(prefix="/api/strategy", tags=["策略引擎"])
  ```

### 响应格式

所有接口统一返回：

```python
# 成功
{"success": True, "data": ..., "message": "操作成功"}

# 分页
{"success": True, "data": {"items": [...], "total": 100, "page": 1, "page_size": 20}}

# 错误
raise HTTPException(status_code=400, detail={"success": False, "message": "参数错误"})
```

### 数据库 Model

- 继承 `Base` + `TimestampMixin`（自动含 `created_at` / `updated_at`）
- 表名使用 snake_case 复数形式
- 字段必须标注 `nullable`、`default` 等约束

```python
from sqlalchemy import Column, Integer, String, Float, Boolean
from common.database import Base, TimestampMixin

class Strategy(Base, TimestampMixin):
    __tablename__ = "strategies"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, comment="策略名称")
    status = Column(String(20), nullable=False, default="draft", comment="draft/running/stopped")
    params = Column(String(2000), nullable=True, comment="策略参数 JSON")
```

### Pydantic Schema

- 请求 Schema 后缀 `Request`，响应 Schema 后缀 `Response`
- 使用 `model_config = {"from_attributes": True}` 支持 ORM 转换

```python
from pydantic import BaseModel
from datetime import datetime

class CreateStrategyRequest(BaseModel):
    name: str
    params: dict | None = None

class StrategyResponse(BaseModel):
    id: int
    name: str
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
```

### 配置管理

- 新增配置项在 `common/config.py` 的 `Settings` 类中添加
- 必须设默认值（开发环境可用的值）
- 同步更新 `.env.example`

```python
class Settings(BaseSettings):
    # 已有...
    NEW_FEATURE_ENABLED: bool = False  # 新增配置

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}
```

---

## 样式 Token 速查

| Token | 值 | 用途 |
|-------|------|------|
| `--color-primary` | #3b82f6 | 主色（选中态、按钮、链接） |
| `--color-background` | #0a0a0f | 页面底色（最深） |
| `--color-surface` | #12121a | 顶栏底色 |
| `--color-surface-container` | #16162a | 输入框、表格行、容器 |
| `--color-surface-container-high` | #1a1a2e | 卡片底色 |
| `--color-surface-container-highest` | #242438 | 弹出层、下拉 |
| `--color-on-surface` | #e5e7eb | 主要文字 |
| `--color-on-surface-variant` | #9ca3af | 次要文字、标签 |
| `--color-up` | #ef4444 | 涨（红，中国惯例） |
| `--color-down` | #22c55e | 跌（绿，中国惯例） |
| `--color-error` | #ef4444 | 错误/危险 |
| `--color-warning` | #f59e0b | 警告 |
| `--color-outline` | #2a2a3e | 边框 |
| `--shadow-card` | 0 2px 8px rgba(0,0,0,0.4) | 卡片阴影 |
| `--shadow-float` | 0 10px 25px rgba(0,0,0,0.5) | 浮层阴影 |
