# GitHub Actions CI/CD

本项目使用 GitHub Actions 进行持续集成和持续部署。

## 工作流

### 1. Docker 镜像构建和发布 (`.github/workflows/docker-publish.yml`)

**触发条件：**
- 推送到 `main` 分支
- 创建标签 `v*`
- 手动触发 (workflow_dispatch)
- Pull Request（仅构建不推送）

**功能：**
- 多架构构建 (linux/amd64, linux/arm64)
- 推送到 GitHub Container Registry (ghcr.io)
- 自动标签管理
- 构建缓存优化

**镜像地址：**
```
ghcr.io/[你的GitHub用户名]/flow2api:latest
ghcr.io/[你的GitHub用户名]/flow2api:v1.1.0
ghcr.io/[你的GitHub用户名]/flow2api:v1.1
ghcr.io/[你的GitHub用户名]/flow2api:v1
```

### 2. 代码质量检查 (`.github/workflows/test.yml`)

**触发条件：**
- 推送到任何分支
- Pull Request

**功能：**
- Python 语法检查
- Ruff 代码风格检查
- 安全漏洞扫描 (Trivy)

### 3. 发布管理 (`.github/workflows/release.yml`)

**触发条件：**
- 创建标签 `v*.*.*`

**功能：**
- 自动生成变更日志
- 创建 GitHub Release

## 使用方法

### 从 GitHub Container Registry 拉取镜像

```bash
# 登录到 GHCR (首次拉取需要)
echo ${{ secrets.GITHUB_TOKEN }} | docker login ghcr.io -u [你的GitHub用户名] --password-stdin

# 拉取最新镜像
docker pull ghcr.io/[你的GitHub用户名]/flow2api:latest

# 拉取指定版本镜像
docker pull ghcr.io/[你的GitHub用户名]/flow2api:v1.1.0

# 运行容器
docker run -d -p 8000:8000 ghcr.io/[你的GitHub用户名]/flow2api:latest
```

### 本地构建镜像

如果你想在本地构建镜像（使用 GitHub Actions 相同的配置）：

```bash
# 克隆仓库
git clone https://github.com/[你的用户名]/flow2api.git
cd flow2api

# 使用 buildx 构建多架构镜像
docker buildx build --platform linux/amd64,linux/arm64 -t flow2api:local .

# 或者构建单架构镜像
docker build -t flow2api:local .
```

## 发布新版本

1. 更新 `CHANGELOG.md`
2. 更新版本号（`src/main.py` 和 `src/api/admin.py`）
3. 创建并推送标签：

```bash
git tag -a v1.2.0 -m "Release v1.2.0"
git push origin v1.2.0
```

GitHub Actions 将自动：
- 构建 Docker 镜像
- 推送到 GHCR
- 创建 Release
- 生成变更日志

## Secrets 配置

本项目使用的 GitHub Actions 不需要额外的 secrets，使用内置的 `GITHUB_TOKEN` 即可。

如果要推送到 Docker Hub，需要添加以下 secrets：
- `DOCKER_USERNAME` - Docker Hub 用户名
- `DOCKER_PASSWORD` - Docker Hub 密码或访问令牌

## 工作流状态徽章

在 README.md 中添加以下徽章以显示构建状态：

```markdown
[![CI](https://github.com/[你的用户名]/flow2api/actions/workflows/test.yml/badge.svg)](https://github.com/[你的用户名]/flow2api/actions/workflows/test.yml)
[![Docker](https://github.com/[你的用户名]/flow2api/actions/workflows/docker-build.yml/badge.svg)](https://github.com/[你的用户名]/flow2api/actions/workflows/docker-build.yml)
```

## 性能优化

### 构建缓存

GitHub Actions 使用 GitHub Actions 缓存来加速构建：

```yaml
cache-from: type=gha
cache-to: type=gha,mode=max
```

### 多架构构建

使用 QEMU 模拟器支持多架构构建：

```yaml
platforms: linux/amd64,linux/arm64
```

## 故障排查

### 构建失败

查看工作流日志：
1. 进入 GitHub 仓库
2. 点击 "Actions" 标签
3. 选择失败的工作流运行
4. 查看详细日志

### 镜像拉取失败

确保已登录到 GHCR：
```bash
echo $GITHUB_TOKEN | docker login ghcr.io -u USERNAME --password-stdin
```

### 权限问题

确保 GitHub Actions 有正确的权限：
```yaml
permissions:
  contents: read
  packages: write
```
