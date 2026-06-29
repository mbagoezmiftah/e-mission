FROM node:25.9.0-alpine3.22
VOLUME /public/plots

RUN mkdir -p /public
WORKDIR /public

RUN npm install -g npm@latest
RUN npm i -g http-server

# Make sure that all vulnerabilities are fixed
RUN npm update -g

COPY client /public/client
COPY *.html /public/

EXPOSE 6060
CMD ["http-server", "-p", "6060"]
