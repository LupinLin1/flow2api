## GitHub Actions 快速入门

### 首次使用

1. **确保仓库设置正确**
   - 进入 GitHub 仓库设置
   - 在 "Actions" -> "General" 中确保 "Workflow permissions" 设置为 "Read and write permissions"

2. **推送代码触发构建**
   ```bash
   git add .
   git commit -m "feat: 添加 GitHub Actions CI/CD"
   git push origin main
   ```

3. **查看构建状态**
   - 访问仓库的 "Actions" 标签页
   - 查看正在运行的工作流

### 使用预构建镜像

#### 方法 1: Docker CLI

```bash
# 拉取最新镜像
docker pull ghcr.io/thesmallhan-cat/flow2api:latest

# 运行容器
docker run -d \
  --name flow2api \
  -p 8000:8000 \
  -v $(pwd)/data:/app/data \
  ghcr.io/thesmallhan-cat/flow2api:latest
```

#### 方法 2: Docker Compose

```bash
# 使用预配置的 compose 文件
docker-compose -f docker-compose.ghcr.yml up -d

# 查看日志
docker-compose -f docker-compose.ghcr.yml logs -f
```

### 发布新版本

1. **更新版本号**
   ```bash
   # 更新 src/main.py 和 src/api/admin.py 中的版本号
   # 例如: 1.1.0 -> 1.2.0
   ```

2. **创建并推送标签**
   ```bash
   git add .
   git commit -m "chore: bump version to 1.2.0"
   git tag -a v1.2.0 -m "Release v1.2.0"
   git push origin main --tags
   ```

3. **自动发布**
   - GitHub Actions 会自动：
     - 构建 Docker 镜像
     - 推送到 GHCR
     - 创建 GitHub Release
     - 生成变更日志

### 工作流说明

#### docker-build.yml
- **触发条件**: push to main/master, tags, manual
- **功能**: 构建并发布 Docker 镜像
- **输出**: 多架构镜像推送到 GHCR

#### test.yml
- **触发条件**: push, pull_request
- **功能**: 代码质量检查和安全扫描
- **输出**: 检查结果和扫描报告

#### release.yml
- **触发条件**: tags (v*.*.*)
- **功能**: 自动创建 Release
- **输出**: GitHub Release 和变更日志

### 故障排查

#### 构建失败
1. 进入 "Actions" 标签页
2. 点击失败的工作流
3. 查看详细日志

#### 镜像拉取失败
```bash
# 确保 Docker 已登录（公共镜像通常不需要）
docker logout ghcr.io

# 重试拉取
docker pull ghcr.io/thesmallhan-cat/flow2api:latest
```

#### 权限错误
在仓库设置中检查：
- Settings -> Actions -> General -> Workflow permissions
- 选择 "Read and write permissions"

### 相关文档

- [GitHub Actions 详细文档](../docs/GITHUB_ACTIONS.md)
- [README.md](../README.md)
- [CHANGELOG.md](../CHANGELOG.md)
