# Use multi-stage build for a smaller final image
FROM python:3.9-slim as builder

# Set working directory
WORKDIR /build

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    wget \
    git \
    gcc \
    g++ \
    make \
    unzip \
    pkg-config \
    python3-dev \
    libc6-dev \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Download and install TA-Lib
RUN wget http://prdownloads.sourceforge.net/ta-lib/ta-lib-0.4.0-src.tar.gz && \
    tar -xvzf ta-lib-0.4.0-src.tar.gz && \
    cd ta-lib/ && \
    ./configure --prefix=/usr && \
    make && \
    make install && \
    cd .. && \
    rm -rf ta-lib-0.4.0-src.tar.gz ta-lib/

# Set environment variables
ENV LD_LIBRARY_PATH=/usr/lib:$LD_LIBRARY_PATH
ENV LIBRARY_PATH=/usr/lib:$LIBRARY_PATH
ENV C_INCLUDE_PATH=/usr/include:$C_INCLUDE_PATH
ENV CPLUS_INCLUDE_PATH=/usr/include:$CPLUS_INCLUDE_PATH
ENV PKG_CONFIG_PATH=/usr/lib/pkgconfig:$PKG_CONFIG_PATH

# Copy requirements files
COPY requirements.txt requirements-ml.txt ./

# Create and activate virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install base dependencies first
RUN pip install --no-cache-dir wheel setuptools numpy==1.24.3 psycopg2-binary

# Install TA-Lib with specific build flags
ENV PYTHON_TALIB=1
RUN CFLAGS="-I/usr/include/ta-lib/" LDFLAGS="-L/usr/lib/" pip install --global-option=build_ext --global-option="-L/usr/lib/" --global-option="-I/usr/include/" ta-lib==0.4.24

# Install main requirements with caching
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements.txt

# Install ML requirements in chunks with increased memory limit
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir tensorflow==2.14.0 && \
    pip install --no-cache-dir torch==2.0.1 && \
    pip install --no-cache-dir transformers==4.34.1 scikit-learn==1.3.1 && \
    pip install --no-cache-dir statsmodels==0.14.0 hmmlearn==0.3.0 arch==6.2.0

# Build frontend
FROM node:18-alpine as frontend-build
WORKDIR /app/frontend

# Clean npm cache first
RUN npm cache clean --force

# Copy package files
COPY web_interface/frontend/package*.json ./

# Remove existing node_modules and any lock files
RUN rm -rf node_modules package-lock.json

# Create .npmrc for legacy peer deps
RUN echo "legacy-peer-deps=true" > .npmrc

# Install React and core dependencies first
RUN npm install --legacy-peer-deps \
    react@18.2.0 \
    react-dom@18.2.0 \
    react-scripts@5.0.1 \
    typescript@4.9.5 \
    web-vitals@2.1.4

# Install UI dependencies
RUN npm install --legacy-peer-deps \
    @chakra-ui/react@2.5.5 \
    @emotion/react@11.10.6 \
    @emotion/styled@11.10.6 \
    framer-motion@10.11.2 \
    chart.js@4.2.1 \
    react-chartjs-2@5.2.0

# Install all type definitions
RUN npm install --save-dev \
    @types/react@18.2.0 \
    @types/react-dom@18.2.0 \
    @types/node@18.15.11 \
    @types/jest@29.5.0 \
    @types/web-vitals@2.1.0 \
    @types/chart.js@2.9.37

# Copy frontend source
COPY web_interface/frontend/ ./

# Create tsconfig.json
RUN echo '{\n\
  "compilerOptions": {\n\
    "target": "es5",\n\
    "lib": ["dom", "dom.iterable", "esnext"],\n\
    "allowJs": true,\n\
    "skipLibCheck": true,\n\
    "esModuleInterop": true,\n\
    "allowSyntheticDefaultImports": true,\n\
    "strict": false,\n\
    "forceConsistentCasingInFileNames": true,\n\
    "noFallthroughCasesInSwitch": true,\n\
    "module": "esnext",\n\
    "moduleResolution": "node",\n\
    "resolveJsonModule": true,\n\
    "isolatedModules": true,\n\
    "noEmit": true,\n\
    "jsx": "react-jsx",\n\
    "baseUrl": "./src",\n\
    "paths": {\n\
      "*": ["*"]\n\
    }\n\
  },\n\
  "include": ["src"],\n\
  "exclude": ["node_modules"]\n\
}' > tsconfig.json

# Create a temporary package.json with the correct types
RUN echo '{\n\
  "name": "retrotrade-frontend",\n\
  "version": "1.0.0",\n\
  "private": true,\n\
  "dependencies": {\n\
    "react": "^18.2.0",\n\
    "react-dom": "^18.2.0",\n\
    "react-scripts": "5.0.1",\n\
    "typescript": "^4.9.5",\n\
    "web-vitals": "^2.1.4",\n\
    "@chakra-ui/react": "^2.5.5",\n\
    "@emotion/react": "^11.10.6",\n\
    "@emotion/styled": "^11.10.6",\n\
    "framer-motion": "^10.11.2",\n\
    "chart.js": "^4.2.1",\n\
    "react-chartjs-2": "^5.2.0"\n\
  },\n\
  "devDependencies": {\n\
    "@types/react": "^18.2.0",\n\
    "@types/react-dom": "^18.2.0",\n\
    "@types/node": "^18.15.11",\n\
    "@types/jest": "^29.5.0",\n\
    "@types/web-vitals": "^2.1.0",\n\
    "@types/chart.js": "^2.9.37"\n\
  },\n\
  "scripts": {\n\
    "start": "react-scripts start",\n\
    "build": "react-scripts build",\n\
    "test": "react-scripts test",\n\
    "eject": "react-scripts eject"\n\
  },\n\
  "eslintConfig": {\n\
    "extends": ["react-app", "react-app/jest"]\n\
  },\n\
  "browserslist": {\n\
    "production": [">0.2%", "not dead", "not op_mini all"],\n\
    "development": ["last 1 chrome version", "last 1 firefox version", "last 1 safari version"]\n\
  }\n\
}' > package.json.tmp && mv package.json.tmp package.json

# Clean build cache and build with increased memory limit
ENV NODE_OPTIONS="--max-old-space-size=4096"
RUN npm cache clean --force && \
    rm -rf build && \
    CI=true npm run build

# Final stage
FROM python:3.9-slim

# Create non-root user
RUN useradd -m -u 1000 trader && \
    mkdir -p /app /app/data /app/logs && \
    chown -R trader:trader /app

# Set working directory
WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv

# Copy only necessary files from builder
COPY --from=builder /usr/lib/libta_lib* /usr/lib/
COPY --from=builder /usr/include/ta-lib /usr/include/ta-lib

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Activate virtual environment
ENV PATH="/opt/venv/bin:$PATH"

# Copy application code
COPY --chown=trader:trader . .

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    LD_LIBRARY_PATH=/usr/lib:$LD_LIBRARY_PATH \
    PYTHONPATH=/app:$PYTHONPATH \
    TZ=UTC

# Create volumes for persistent data and logs
VOLUME ["/app/data", "/app/logs"]

# Expose port
EXPOSE 8000

# Switch to non-root user
USER trader

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Set default command with proper signal handling
ENTRYPOINT ["python"]
CMD ["main.py"] 