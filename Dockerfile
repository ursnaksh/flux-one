FROM node:24-alpine

WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --omit=dev --ignore-scripts
COPY index.html ./index.html
COPY backend/*.mjs ./backend/

ENV PORT=10000
ENV NODE_ENV=production
EXPOSE 10000

CMD ["npm", "start"]
