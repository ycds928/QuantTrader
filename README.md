# QuantFlow — 个人量化交易平台

前后端分离的量化交易 Web 平台。前端 Vite + React + TypeScript SPA，后端 Python FastAPI + SQLAlchemy + MySQL 8.0。深色 TradingView 风格，中国惯例红涨绿跌。

## 环境要求

| 依赖 | 最低版本 |
|------|----------|
| Node.js | 18+ |
| pnpm | 8+ |
| Python | 3.12+ |
| MySQL | 8.0+ |

## 快速开始

### 1. 克隆仓库

```bash
git clone <repo-url> && cd quantflow
```

### 2. 配置环境变量

```bash
cp .env.example .env
```

编辑 `.env`，至少填写 MySQL 连接信息：

```env
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=quant_user
MYSQL_PASSWORD=your_password
MYSQL_DATABASE=quant_trading
```

### 3. 安装依赖

```bash
# 前端
cd frontend
pnpm install

# 后端
cd ../backend
pip install -r requirements.txt
```

### 4. 初始化数据库

确保 MySQL 服务已启动且 `.env` 中的数据库已创建：

```sql
CREATE DATABASE IF NOT EXISTS quant_trading
  DEFAULT CHARACTER SET utf8mb4
  DEFAULT COLLATE utf8mb4_unicode_ci;
```

运行迁移（当项目有 Alembic 迁移后）：

```bash
cd backend
alembic upgrade head
```

### 5. 启动开发服务器

需要两个终端分别启动前后端，或者使用一键脚本：

**方式一：分别启动（推荐开发时使用）**

```bash
# 终端 1 — 后端（端口 8000）
cd backend
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# 终端 2 — 前端（端口 5000，自带 API 代理）
cd frontend
pnpm dev
```

前端 Vite 会自动将 `/api/*` 和 `/ws/*` 请求代理到后端 `localhost:8000`，无需额外配置。

**方式二：一键启动**

```bash
bash .cozeproj/dev-start.sh
```

此脚本后台启动后端，前台启动前端。

### 6. 访问

- 前端页面：http://localhost:5000
- 后端 API 文档：http://localhost:8000/docs（FastAPI 自动生成 Swagger UI）
- 健康检查：http://localhost:5000/api/health

## 生产构建

```bash
# 构建前端
cd frontend && pnpm run build

# 构建产物在 frontend/dist/，由 FastAPI 托管静态文件
# 启动生产服务（端口 5000）
cd ../backend
python -m uvicorn main:app --host 0.0.0.0 --port 5000
```

## 项目结构

```
.
├── frontend/                   # 前端 Vite + React SPA
│   ├── src/
│   │   ├── common/             # 公共模块（专人维护）
│   │   ├── api-data/           # 模块1: 行情数据
│   │   ├── account-trading/    # 模块2: 帐户与交易
│   │   ├── strategy-engine/    # 模块3: 策略引擎
│   │   ├── strategy-execution/ # 模块4: 策略执行与风控
│   │   ├── review-analysis/    # 模块5: 复盘分析
│   │   └── history-replay/     # 模块6: 历史回放
│   └── vite.config.ts
├── backend/                    # 后端 FastAPI
│   ├── common/                 # 公共模块（专人维护）
│   ├── api_data/               # 模块1
│   ├── account_trading/        # 模块2
│   ├── strategy_engine/        # 模块3
│   ├── strategy_execution/     # 模块4
│   ├── review_analysis/        # 模块5
│   ├── history_replay/         # 模块6
│   ├── alembic/                # 数据库迁移
│   └── main.py
├── .env / .env.example         # 环境变量
├── .coze                       # 部署配置
└── .cozeproj/                  # 启动脚本
```

## 详细文档

- [开发指南](./DEVELOPMENT.md) — 架构、贡献规范、接口约定
- [代码规范](./CODE_STYLE.md) — 前后端代码风格与约束
