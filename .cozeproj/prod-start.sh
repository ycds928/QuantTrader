#!/bin/bash
# 生产环境启动脚本：启动后端 FastAPI（前端已 build 为静态文件由 FastAPI 托管）

cd /workspace/projects/backend
exec python -m uvicorn main:app --host 0.0.0.0 --port 5000
