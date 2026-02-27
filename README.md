# Flow2API

<div align="center">

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/fastapi-0.119.0-green.svg)](https://fastapi.tiangolo.com/)
[![Docker](https://img.shields.io/badge/docker-supported-blue.svg)](https://www.docker.com/)
[![CI](https://github.com/LupinLin1/flow2api/actions/workflows/test.yml/badge.svg)](https://github.com/LupinLin1/flow2api/actions/workflows/test.yml)
[![Docker Publish](https://github.com/LupinLin1/flow2api/actions/workflows/docker-publish.yml/badge.svg)](https://github.com/LupinLin1/flow2api/actions/workflows/docker-publish.yml)
[![Docker Image](https://img.shields.io/badge/docker-ghcr.io-blue)](https://github.com/LupinLin1/flow2api/pkgs/container/flow2api)

**一个功能完整的 OpenAI 兼容 API 服务，为 Flow 提供统一的接口**

</div>

## ✨ 核心特性

- 🎨 **文生图** / **图生图**
- 🎬 **文生视频** / **图生视频**
- 🎞️ **首尾帧视频**
- 🔄 **AT/ST自动刷新** - AT 过期自动刷新，ST 过期时自动通过浏览器更新（personal 模式）
- 📊 **余额显示** - 实时查询和显示 VideoFX Credits
- 🚀 **负载均衡** - 多 Token 轮询和并发控制
- 🌐 **代理支持** - 支持 HTTP/SOCKS5 代理
- 📱 **Web 管理界面** - 直观的 Token 和配置管理
- 🎨 **图片生成连续对话**

## 🚀 快速开始

### 前置要求

- Docker 和 Docker Compose（推荐）
- 或 Python 3.8+

- 由于Flow增加了额外的验证码，你可以自行选择使用浏览器打码或第三发打码：
注册[YesCaptcha](https://yescaptcha.com/i/13Xd8K)并获取api key，将其填入系统配置页面```YesCaptcha API密钥```区域

- 自动更新st浏览器拓展：[Flow2API-Token-Updater](https://github.com/TheSmallHanCat/Flow2API-Token-Updater)

### 方式一：Docker 部署（推荐）

#### 使用预构建镜像（最快）

直接从 GitHub Container Registry 拉取预构建的镜像：

```bash
# 拉取最新镜像
docker pull ghcr.io/lupinlin1/flow2api:latest

# 运行容器
docker run -d \
  --name flow2api \
  -p 8000:8000 \
  -v $(pwd)/data:/app/data \
  ghcr.io/lupinlin1/flow2api:latest

# 查看日志
docker logs -f flow2api
```

**指定版本：**
```bash
# 拉取特定版本
docker pull ghcr.io/lupinlin1/flow2api:v1.1.0

# 运行特定版本
docker run -d -p 8000:8000 ghcr.io/lupinlin1/flow2api:v1.1.0
```

#### 从源码构建

```bash
# 克隆项目
git clone https://github.com/TheSmallHanCat/flow2api.git
cd flow2api

# 启动服务
docker-compose up -d

# 查看日志
docker-compose logs -f
```

#### WARP 模式（使用代理）

```bash
# 使用 WARP 代理启动
docker-compose -f docker-compose.warp.yml up -d

# 查看日志
docker-compose -f docker-compose.warp.yml logs -f
```

### 方式二：本地部署

```bash
# 克隆项目
git clone https://github.com/TheSmallHanCat/flow2api.git
cd sora2api

# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 启动服务
python main.py
```

### 方式三：VPS 环境部署

如果你的 VPS 没有图形界面（如 Ubuntu Server、CentOS 等），需要安装 Xvfb（虚拟显示）来支持有头浏览器打码功能。

#### 安装 Xvfb

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install -y xvfb x11-utils
```

**CentOS/RHEL:**
```bash
sudo yum install -y xorg-x11-server-Xvfb
```

#### 使用 xvfb-run 启动

安装 Xvfb 后，使用 xvfb-run 启动程序即可在有头浏览器模式下运行：

```bash
xvfb-run -a --server-args="-screen 0 1280x720x24" python main.py
```

参数说明：
- `-a`: 自动选择可用的显示编号
- `-screen 0 1280x720x24`: 创建 0 号屏幕，分辨率 1280x720，色深 24

#### Docker 部署（已内置 Xvfb）

更新后的 Dockerfile 已自动安装 Xvfb，无需额外配置：

```bash
# 重新构建镜像
docker build -t flow2api:latest .

# 运行容器
docker run -p 8000:8000 flow2api:latest
```

#### 验证 Xvfb 环境

测试 Xvfb 是否可用：

```bash
xvfb-run -a python -c "import os; print('DISPLAY:', os.environ.get('DISPLAY'))"
```

### 首次访问

服务启动后,访问管理后台: **http://localhost:8000**,首次登录后请立即修改密码!

- **用户名**: `admin`
- **密码**: `admin`

## 📋 支持的模型

### 图片生成

| 模型名称 | 说明| 尺寸 |
|---------|--------|--------|
| `gemini-2.5-flash-image-landscape` | 图/文生图 | 横屏 |
| `gemini-2.5-flash-image-portrait` | 图/文生图 | 竖屏 |
| `gemini-3.0-pro-image-landscape` | 图/文生图 | 横屏 |
| `gemini-3.0-pro-image-portrait` | 图/文生图 | 竖屏 |
| `gemini-3.1-flash-image-landscape` | 图/文生图 | 横屏 |
| `gemini-3.1-flash-image-portrait` | 图/文生图 | 竖屏 |
| `imagen-4.0-generate-preview-landscape` | 图/文生图 | 横屏 |
| `imagen-4.0-generate-preview-portrait` | 图/文生图 | 竖屏 |

### 视频生成

#### 文生视频 (T2V - Text to Video)
⚠️ **不支持上传图片**

| 模型名称 | 说明| 尺寸 |
|---------|---------|--------|
| `veo_3_1_t2v_fast_portrait` | 文生视频 | 竖屏 |
| `veo_3_1_t2v_fast_landscape` | 文生视频 | 横屏 |
| `veo_2_1_fast_d_15_t2v_portrait` | 文生视频 | 竖屏 |
| `veo_2_1_fast_d_15_t2v_landscape` | 文生视频 | 横屏 |
| `veo_2_0_t2v_portrait` | 文生视频 | 竖屏 |
| `veo_2_0_t2v_landscape` | 文生视频 | 横屏 |

#### 首尾帧模型 (I2V - Image to Video)
📸 **支持1-2张图片：1张作为首帧，2张作为首尾帧**

> 💡 **自动适配**：系统会根据图片数量自动选择对应的 model_key
> - **单帧模式**（1张图）：使用首帧生成视频
> - **双帧模式**（2张图）：使用首帧+尾帧生成过渡视频

| 模型名称 | 说明| 尺寸 |
|---------|---------|--------|
| `veo_3_1_i2v_s_fast_fl_portrait` | 图生视频 | 竖屏 |
| `veo_3_1_i2v_s_fast_fl_landscape` | 图生视频 | 横屏 |
| `veo_2_1_fast_d_15_i2v_portrait` | 图生视频 | 竖屏 |
| `veo_2_1_fast_d_15_i2v_landscape` | 图生视频 | 横屏 |
| `veo_2_0_i2v_portrait` | 图生视频 | 竖屏 |
| `veo_2_0_i2v_landscape` | 图生视频 | 横屏 |

#### 多图生成 (R2V - Reference Images to Video)
🖼️ **支持多张图片**

| 模型名称 | 说明| 尺寸 |
|---------|---------|--------|
| `veo_3_0_r2v_fast_portrait` | 图生视频 | 竖屏 |
| `veo_3_0_r2v_fast_landscape` | 图生视频 | 横屏 |

## 📡 API 使用示例（需要使用流式）

### 文生图

```bash
curl -X POST "http://localhost:8000/v1/chat/completions" \
  -H "Authorization: Bearer han1234" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gemini-2.5-flash-image-landscape",
    "messages": [
      {
        "role": "user",
        "content": "一只可爱的猫咪在花园里玩耍"
      }
    ],
    "stream": true
  }'
```

### 图生图

```bash
curl -X POST "http://localhost:8000/v1/chat/completions" \
  -H "Authorization: Bearer han1234" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "imagen-4.0-generate-preview-landscape",
    "messages": [
      {
        "role": "user",
        "content": [
          {
            "type": "text",
            "text": "将这张图片变成水彩画风格"
          },
          {
            "type": "image_url",
            "image_url": {
              "url": "data:image/jpeg;base64,<base64_encoded_image>"
            }
          }
        ]
      }
    ],
    "stream": true
  }'
```

### 文生视频

```bash
curl -X POST "http://localhost:8000/v1/chat/completions" \
  -H "Authorization: Bearer han1234" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "veo_3_1_t2v_fast_landscape",
    "messages": [
      {
        "role": "user",
        "content": "一只小猫在草地上追逐蝴蝶"
      }
    ],
    "stream": true
  }'
```

### 首尾帧生成视频

```bash
curl -X POST "http://localhost:8000/v1/chat/completions" \
  -H "Authorization: Bearer han1234" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "veo_3_1_i2v_s_fast_fl_landscape",
    "messages": [
      {
        "role": "user",
        "content": [
          {
            "type": "text",
            "text": "从第一张图过渡到第二张图"
          },
          {
            "type": "image_url",
            "image_url": {
              "url": "data:image/jpeg;base64,<首帧base64>"
            }
          },
          {
            "type": "image_url",
            "image_url": {
              "url": "data:image/jpeg;base64,<尾帧base64>"
            }
          }
        ]
      }
    ],
    "stream": true
  }'
```

---

## 📄 许可证

本项目采用 MIT 许可证。详见 [LICENSE](LICENSE) 文件。

---

## 🙏 致谢

- [PearNoDec](https://github.com/PearNoDec) 提供的YesCaptcha打码方案
- [raomaiping](https://github.com/raomaiping) 提供的无头打码方案
感谢所有贡献者和使用者的支持！

---

## 📞 联系方式

- 提交 Issue：[GitHub Issues](https://github.com/TheSmallHanCat/flow2api/issues)

---

**⭐ 如果这个项目对你有帮助，请给个 Star！**

## Star History

[![Star History Chart](https://api.star-history.com/svg?repos=LupinLin1/flow2api&type=date&legend=top-left)](https://www.star-history.com/#LupinLin1/flow2api&type=date&legend=top-left)
