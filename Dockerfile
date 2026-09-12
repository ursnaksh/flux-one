FROM node:24-alpine

WORKDIR /app
COPY index.html ./index.html
COPY backend/server.mjs ./backend/server.mjs

ENV PORT=10000
EXPOSE 10000

CMD ["node", "backend/server.mjs"]
