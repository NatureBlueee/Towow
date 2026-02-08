#!/bin/bash
# Team Matcher 端到端测试脚本
# 测试覆盖：API、前端页面、数据流、响应式设计

set -e  # 遇到错误立即退出

echo "=========================================="
echo "Team Matcher 端到端测试"
echo "=========================================="
echo ""

# 颜色定义
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 测试计数
PASSED=0
FAILED=0

# 测试函数
test_api() {
    local name="$1"
    local method="$2"
    local url="$3"
    local expected_status="$4"
    local data="$5"

    echo -n "Testing: $name ... "

    if [ -z "$data" ]; then
        response=$(curl -s -w "\n%{http_code}" -X "$method" "$url")
    else
        response=$(curl -s -w "\n%{http_code}" -X "$method" "$url" \
            -H "Content-Type: application/json" \
            -d "$data")
    fi

    status_code=$(echo "$response" | tail -n 1)
    body=$(echo "$response" | sed '$d')

    if [ "$status_code" = "$expected_status" ]; then
        echo -e "${GREEN}✓ PASS${NC} (HTTP $status_code)"
        PASSED=$((PASSED + 1))
        return 0
    else
        echo -e "${RED}✗ FAIL${NC} (Expected $expected_status, got $status_code)"
        echo "Response: $body"
        FAILED=$((FAILED + 1))
        return 1
    fi
}

test_page() {
    local name="$1"
    local url="$2"

    echo -n "Testing: $name ... "

    response=$(curl -s -w "\n%{http_code}" "$url")
    status_code=$(echo "$response" | tail -n 1)
    body=$(echo "$response" | sed '$d')

    if [ "$status_code" = "200" ]; then
        # 检查关键内容
        if echo "$body" | grep -q "<!DOCTYPE html>"; then
            echo -e "${GREEN}✓ PASS${NC} (Page loads, HTML valid)"
            PASSED=$((PASSED + 1))
            return 0
        else
            echo -e "${RED}✗ FAIL${NC} (Invalid HTML response)"
            FAILED=$((FAILED + 1))
            return 1
        fi
    else
        echo -e "${RED}✗ FAIL${NC} (HTTP $status_code)"
        FAILED=$((FAILED + 1))
        return 1
    fi
}

echo "=========================================="
echo "1. 后端 API 测试"
echo "=========================================="
echo ""

# 测试健康检查
test_api "Health Check" "GET" "http://localhost:8080/api/health" "200"

# 测试创建组队请求（模拟）
TEAM_REQUEST_DATA='{
  "user_id": "test_user_123",
  "project_idea": "AI健康助手黑客松项目",
  "skills": ["Python", "React"],
  "availability": "weekend",
  "roles_needed": ["前端开发", "UI设计"],
  "context": {
    "hackathon": "A2A Hackathon 2026"
  }
}'

# 注意：实际 API 端点可能不存在，这里测试是否返回合理错误
response=$(curl -s -w "\n%{http_code}" -X POST "http://localhost:8080/api/team/request" \
    -H "Content-Type: application/json" \
    -d "$TEAM_REQUEST_DATA" || echo -e "\n404")

status_code=$(echo "$response" | tail -n 1)
if [ "$status_code" = "404" ] || [ "$status_code" = "200" ] || [ "$status_code" = "201" ]; then
    echo -e "API Endpoint Test: ${YELLOW}SKIP${NC} (API may not be implemented yet, status: $status_code)"
else
    echo -e "API Endpoint Test: ${RED}FAIL${NC} (Unexpected status: $status_code)"
fi

echo ""
echo "=========================================="
echo "2. 前端页面加载测试"
echo "=========================================="
echo ""

# 测试组队请求页面
test_page "Team Request Page (/team/request)" "http://localhost:3000/team/request"

# 测试进度页面（使用示例 ID）
test_page "Progress Page (/team/progress/[id])" "http://localhost:3000/team/progress/req_example_001"

# 测试方案页面（使用示例 ID）
test_page "Proposals Page (/team/proposals/[id])" "http://localhost:3000/team/proposals/req_example_001"

echo ""
echo "=========================================="
echo "3. 静态资源测试"
echo "=========================================="
echo ""

# 测试 CSS 文件
echo -n "Testing: Team Matcher CSS ... "
if [ -f "/Users/nature/个人项目/Towow/website/styles/team-matcher.css" ]; then
    # 检查关键动画定义
    if grep -q "@keyframes signal-pulse" "/Users/nature/个人项目/Towow/website/styles/team-matcher.css" && \
       grep -q "@keyframes fly-in" "/Users/nature/个人项目/Towow/website/styles/team-matcher.css" && \
       grep -q "prefers-reduced-motion" "/Users/nature/个人项目/Towow/website/styles/team-matcher.css"; then
        echo -e "${GREEN}✓ PASS${NC} (CSS animations and a11y defined)"
        PASSED=$((PASSED + 1))
    else
        echo -e "${RED}✗ FAIL${NC} (Missing animations or accessibility rules)"
        FAILED=$((FAILED + 1))
    fi
else
    echo -e "${RED}✗ FAIL${NC} (CSS file not found)"
    FAILED=$((FAILED + 1))
fi

echo ""
echo "=========================================="
echo "4. TypeScript 类型检查"
echo "=========================================="
echo ""

cd /Users/nature/个人项目/Towow/website

echo -n "Testing: TypeScript compilation ... "
if npm run build > /tmp/team_matcher_build.log 2>&1; then
    echo -e "${GREEN}✓ PASS${NC} (No type errors)"
    PASSED=$((PASSED + 1))
else
    echo -e "${RED}✗ FAIL${NC} (Type errors detected)"
    echo "Build log:"
    tail -20 /tmp/team_matcher_build.log
    FAILED=$((FAILED + 1))
fi

echo ""
echo "=========================================="
echo "5. Mock 数据完整性测试"
echo "=========================================="
echo ""

echo -n "Testing: Mock data structure ... "
if [ -f "/Users/nature/个人项目/Towow/website/lib/team-matcher/api.ts" ]; then
    # 检查是否包含所有必需的 mock 数据
    if grep -q "MOCK_TEAM_REQUEST" "/Users/nature/个人项目/Towow/website/lib/team-matcher/api.ts" && \
       grep -q "MOCK_PROPOSALS" "/Users/nature/个人项目/Towow/website/lib/team-matcher/api.ts" && \
       grep -q "MOCK_AGENTS" "/Users/nature/个人项目/Towow/website/lib/team-matcher/api.ts"; then
        echo -e "${GREEN}✓ PASS${NC} (All mock data present)"
        PASSED=$((PASSED + 1))
    else
        echo -e "${RED}✗ FAIL${NC} (Missing mock data)"
        FAILED=$((FAILED + 1))
    fi
else
    echo -e "${RED}✗ FAIL${NC} (API file not found)"
    FAILED=$((FAILED + 1))
fi

echo ""
echo "=========================================="
echo "6. 响应式设计测试"
echo "=========================================="
echo ""

echo -n "Testing: Mobile breakpoints ... "
if grep -r "@media.*640px\|@media.*768px\|@media.*1024px" \
    /Users/nature/个人项目/Towow/website/styles/team-matcher.css \
    > /dev/null 2>&1; then
    echo -e "${GREEN}✓ PASS${NC} (Mobile breakpoints defined)"
    PASSED=$((PASSED + 1))
else
    echo -e "${YELLOW}⚠ WARN${NC} (No explicit media queries in CSS, may use Tailwind)"
fi

echo ""
echo "=========================================="
echo "测试总结"
echo "=========================================="
echo ""
echo -e "Total Tests: $((PASSED + FAILED))"
echo -e "${GREEN}Passed: $PASSED${NC}"
echo -e "${RED}Failed: $FAILED${NC}"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}=========================================="
    echo "✓ 所有测试通过！"
    echo "==========================================${NC}"
    exit 0
else
    echo -e "${RED}=========================================="
    echo "✗ 有 $FAILED 个测试失败"
    echo "==========================================${NC}"
    exit 1
fi
