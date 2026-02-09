#!/bin/bash
# AToA 应用生态 — 一键启动所有应用
#
# 用法：
#   cd apps && ./start_all.sh
#
# 端口分配：
#   8100 — S1 黑客松组队
#   8101 — S2 技能交换
#   8102 — R1 AI 招聘
#   8103 — M1 AI 相亲
#   8200 — App Store 应用商城
#
# 环境变量：
#   TOWOW_ANTHROPIC_API_KEY — Claude API Key（可选，无则使用 Mock LLM）

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "========================================="
echo "  AToA 应用生态 — 启动中"
echo "========================================="
echo ""

# 确保在虚拟环境中
if [ -z "$VIRTUAL_ENV" ]; then
    if [ -f "$PROJECT_ROOT/backend/venv/bin/activate" ]; then
        source "$PROJECT_ROOT/backend/venv/bin/activate"
        echo "[OK] 激活虚拟环境"
    else
        echo "[WARN] 未找到虚拟环境，请确保已安装依赖"
    fi
fi

# 添加项目路径
export PYTHONPATH="$PROJECT_ROOT:$PROJECT_ROOT/backend:$PYTHONPATH"

echo ""
echo "启动应用..."
echo ""

# 启动各应用（后台运行）
cd "$SCRIPT_DIR"

echo "[S1] 黑客松组队 — http://localhost:8100"
uvicorn S1_hackathon.backend.app:app --host 0.0.0.0 --port 8100 &
PID_S1=$!

echo "[S2] 技能交换 — http://localhost:8101"
uvicorn S2_skill_exchange.backend.app:app --host 0.0.0.0 --port 8101 &
PID_S2=$!

echo "[R1] AI 招聘 — http://localhost:8102"
uvicorn R1_recruitment.backend.app:app --host 0.0.0.0 --port 8102 &
PID_R1=$!

echo "[M1] AI 相亲 — http://localhost:8103"
uvicorn M1_matchmaking.backend.app:app --host 0.0.0.0 --port 8103 &
PID_M1=$!

# 等待应用启动
sleep 3

echo "[AS] App Store 应用商城 — http://localhost:8200"
ATOA_APPS="http://localhost:8100,http://localhost:8101,http://localhost:8102,http://localhost:8103" \
    uvicorn app_store.backend.app:app --host 0.0.0.0 --port 8200 &
PID_AS=$!

echo ""
echo "========================================="
echo "  所有应用已启动"
echo ""
echo "  S1 黑客松组队:  http://localhost:8100"
echo "  S2 技能交换:    http://localhost:8101"
echo "  R1 AI 招聘:     http://localhost:8102"
echo "  M1 AI 相亲:     http://localhost:8103"
echo "  App Store:      http://localhost:8200"
echo ""
echo "  按 Ctrl+C 停止所有应用"
echo "========================================="

# 等待所有进程
trap "kill $PID_S1 $PID_S2 $PID_R1 $PID_M1 $PID_AS 2>/dev/null; exit" SIGINT SIGTERM
wait
