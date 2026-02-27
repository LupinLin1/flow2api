# 变更日志

## [1.1.0] - 2026-02-28

### 新增
- ✨ 添加 Xvfb 虚拟显示支持
  - 支持 VPS/无显示服务器环境运行有头浏览器打码
  - Docker 镜像自动安装并配置 Xvfb
  - 从检测 Docker 环境改为检测显示环境（更灵活）

### 改进
- 🔧 环境检测逻辑优化
  - 使用 `_has_display_environment()` 替代 `_is_running_in_docker()`
  - 支持 DISPLAY 环境变量和 Xvfb 虚拟显示检测
  - 更友好的错误提示信息

### 文档
- 📝 添加 VPS 环境部署章节
  - Ubuntu/Debian 和 CentOS/RHEL 的 Xvfb 安装说明
  - xvfb-run 使用示例和参数说明
  - Xvfb 环境验证方法

### 工具
- 🛠️ 新增 VPS 环境检查脚本 (`scripts/check_vps_env.sh`)
  - 自动检测 Xvfb 和依赖组件
  - 提供安装指导

### CI/CD
- 🚀 添加 GitHub Actions 工作流
  - 自动构建 Docker 镜像并推送到 GitHub Container Registry
  - 多架构支持 (linux/amd64, linux/arm64)
  - 代码质量检查和安全扫描
  - 自动创建 Release 和生成变更日志
- 📦 新增 `docker-compose.ghcr.yml` 用于使用预构建镜像
- 📖 添加 GitHub Actions 使用文档 (`docs/GITHUB_ACTIONS.md`)

## [1.0.0] - 之前版本
- 初始版本
- 支持 Veo 3.1 视频生成
- 支持图像生成和放大
- 有头浏览器和第三方打码支持
- Web 管理界面
