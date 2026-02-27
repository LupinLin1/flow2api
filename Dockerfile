FROM python:3.11-slim

WORKDIR /app

# 安装 Xvfb 虚拟显示和浏览器依赖
RUN apt-get update && apt-get install -y \
    xvfb \
    x11-utils \
    && rm -rf /var/lib/apt/lists/*

# 安装 Python 依赖
COPY requirements.txt .
RUN pip install --no-cache-dir --root-user-action=ignore -r requirements.txt

COPY . .

EXPOSE 8000

# 使用 xvfb-run 启动（设置虚拟显示为 99 号屏幕，分辨率 1280x720x24）
CMD ["xvfb-run", "-a", "--server-args=-screen 0 1280x720x24", "python", "main.py"]
