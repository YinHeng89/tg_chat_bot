# ===== 阶段 1: 构建前端 =====
FROM node:20-alpine AS frontend-builder

WORKDIR /frontend
COPY frontend/package.json ./
RUN npm install

COPY frontend/ ./
RUN npm run build

# ===== 阶段 2: Python 后端 =====
FROM python:3.11-slim

WORKDIR /app

# 安装依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制源码
COPY . .

# 复制前端构建产物
COPY --from=frontend-builder /frontend/dist ./frontend/dist

# 创建数据和日志目录
RUN mkdir -p data logs workspace

EXPOSE 8000

CMD ["python", "main.py"]
