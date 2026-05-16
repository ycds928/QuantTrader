#!/bin/bash
# 开发环境启动脚本：同时启动后端 FastAPI 和前端 Vite

# 启动后端 FastAPI（后台）
cd /workspace/projects/backend
nohup python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload > /app/work/logs/bypass/app.log 2>&1 &

# 启动前端 Vite（前台，端口 5000）
cd /workspace/projects/frontend
exec npx vite --host 0.0.0.0 --port 5000
