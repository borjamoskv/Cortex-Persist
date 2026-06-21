FROM node:20-alpine

WORKDIR /app
COPY brain-swarm/package.json /app/brain-swarm/package.json
COPY brain-swarm/src /app/brain-swarm/src
RUN cd /app/brain-swarm && npm install --omit=dev

WORKDIR /app/brain-swarm
CMD ["npm", "run", "coordinator"]
