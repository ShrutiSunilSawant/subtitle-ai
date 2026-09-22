# ================================================================
# Frontend Dockerfile — React + Vite
# ================================================================

FROM node:20-alpine

WORKDIR /app

# Copy package files first (layer caching)
COPY package.json ./

# Install dependencies
RUN npm install

# Copy source code
COPY . .

# Expose Vite dev server port
EXPOSE 5173

# Run Vite dev server with host binding for Docker
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
