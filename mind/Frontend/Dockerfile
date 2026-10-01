FROM node:20-alpine AS builder
WORKDIR /mind/frontend
COPY package*.json ./
RUN npm install


FROM node:20-alpine
WORKDIR /mind/frontend
COPY --from=builder /mind/frontend/node_modules ./node_modules
COPY . .
EXPOSE 5173
CMD ["npm", "run", "dev", "--", "--host"]