#!/bin/bash
# ToWow 开发环境启动脚本
# 用法: ./start-dev.sh

echo "🚀 启动 ToWow 开发环境..."

# 杀死现有进程
echo "清理现有进程..."
lsof -ti:8000 | xargs kill -9 2>/dev/null
lsof -ti:5173 | xargs kill -9 2>/dev/null
sleep 2

# 启动后端
echo ""
echo "=========================================="
echo "📦 启动后端 (端口 8000)"
echo "=========================================="
echo "请在新终端运行:"
echo ""
echo "  cd /Users/nature/个人项目/Towow/towow"
echo "  source venv/bin/activate"
echo "  python -m uvicorn api.main:app --reload --host 0.0.0.0 --port 8000"
echo ""

# 启动前端
echo "=========================================="
echo "🎨 启动前端 (端口 5173)"
echo "=========================================="
echo "请在另一个新终端运行:"
echo ""
echo "  cd /Users/nature/个人项目/Towow/towow-frontend"
echo "  npm run dev"
echo ""

echo "=========================================="
echo "📋 快速启动命令"
echo "=========================================="
echo ""
echo "# 终端1 - 后端 (复制粘贴):"
echo "cd /Users/nature/个人项目/Towow/towow && source venv/bin/activate && python -m uvicorn api.main:app --reload --host 0.0.0.0 --port 8000"
echo ""
echo "# 终端2 - 前端 (复制粘贴):"
echo "cd /Users/nature/个人项目/Towow/towow-frontend && npm run dev"
echo ""
echo "=========================================="
echo "🌐 访问地址"
echo "=========================================="
echo "前端: http://localhost:5173"
echo "后端: http://localhost:8000"
echo "API文档: http://localhost:8000/docs"
echo ""
