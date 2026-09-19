FROM python:3.14.7-slim

# 设置工作目录
WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    tzdata \
    && ln -fs /usr/share/zoneinfo/Asia/Shanghai /etc/localtime \
    && dpkg-reconfigure -f noninteractive tzdata \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件并安装
COPY requirements.txt .
RUN pip install --no-cache-dir --require-hashes -r requirements.txt

# 复制应用代码
COPY . .

# 设置环境变量
ENV PYTHONUNBUFFERED=1

RUN useradd --create-home --uid 10001 appuser \
    && chown -R appuser:appuser /app \
    && chmod +x /app/docker-entrypoint.sh

# 启动命令
ENTRYPOINT ["/app/docker-entrypoint.sh"]
CMD ["python", "main.py"]
