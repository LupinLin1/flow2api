#!/bin/bash
# VPS 环境检查脚本
# 用于验证 VPS 是否具备运行有头浏览器打码的条件

echo "================================================"
echo "VPS 环境检查脚本"
echo "================================================"
echo ""

# 颜色定义
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

check_count=0
pass_count=0

# 检查函数
check_item() {
    local name=$1
    local command=$2
    local required=$3

    check_count=$((check_count + 1))
    echo -n "[$check_count] 检查 $name... "

    if eval "$command" > /dev/null 2>&1; then
        echo -e "${GREEN}✓ 已安装${NC}"
        pass_count=$((pass_count + 1))
        return 0
    else
        if [ "$required" = "true" ]; then
            echo -e "${RED}✗ 未安装（必需）${NC}"
            return 1
        else
            echo -e "${YELLOW}⊝ 未安装（可选）${NC}"
            return 0
        fi
    fi
}

echo "=== 必需组件检查 ==="
echo ""

check_item "Python 3" "command -v python3" "true"
check_item "pip" "command -v pip3" "true"
check_item "Xvfb" "command -v Xvfb" "true"
check_item "xvfb-run" "command -v xvfb-run" "true"

echo ""
echo "=== 可选组件检查 ==="
echo ""

check_item "Git" "command -v git" "false"
check_item "Docker" "command -v docker" "false"
check_item "Docker Compose" "command -v docker-compose" "false"

echo ""
echo "=== 测试 Xvfb 功能 ==="
echo ""

echo "测试 Xvfb 是否能正常启动..."
if timeout 5 xvfb-run -a --server-args="-screen 0 1280x720x24" python3 -c "import os; print('DISPLAY:', os.environ.get('DISPLAY'))" 2>/dev/null; then
    echo -e "${GREEN}✓ Xvfb 功能正常${NC}"
    pass_count=$((pass_count + 1))
else
    echo -e "${RED}✗ Xvfb 测试失败${NC}"
fi

echo ""
echo "================================================"
echo "检查结果汇总"
echo "================================================"
echo ""
echo "总检查项: $check_count"
echo -e "通过: ${GREEN}$pass_count${NC}"
echo -e "失败: ${RED}$((check_count - pass_count))${NC}"
echo ""

if [ $pass_count -eq $check_count ]; then
    echo -e "${GREEN}✅ 所有检查通过！可以部署有头浏览器打码服务。${NC}"
    echo ""
    echo "启动命令："
    echo "  xvfb-run -a --server-args=\"-screen 0 1280x720x24\" python3 main.py"
    exit 0
else
    echo -e "${RED}❌ 部分检查未通过，请安装缺失的组件。${NC}"
    echo ""
    echo "安装命令："
    echo "  Ubuntu/Debian:"
    echo "    sudo apt-get update"
    echo "    sudo apt-get install -y xvfb x11-utils python3 python3-pip"
    echo ""
    echo "  CentOS/RHEL:"
    echo "    sudo yum install -y xorg-x11-server-Xvfb python3 python3-pip"
    exit 1
fi
