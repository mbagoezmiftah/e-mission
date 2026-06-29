#!/usr/bin/env node

const fs = require('fs');
const http = require('http');
const path = require('path');

const root = path.join(__dirname, '..', 'www');
const port = Number(process.env.PORT || 3000);

const mimeTypes = {
  '.css': 'text/css',
  '.html': 'text/html',
  '.js': 'text/javascript',
  '.json': 'application/json',
  '.png': 'image/png',
  '.svg': 'image/svg+xml',
  '.ttf': 'font/ttf',
  '.woff': 'font/woff',
  '.woff2': 'font/woff2',
};

function send(res, status, body, type = 'text/plain') {
  res.writeHead(status, {
    'Content-Type': type,
    'Cache-Control': 'no-store',
  });
  res.end(body);
}

function resolveRequestPath(url) {
  const pathname = decodeURIComponent(new URL(url, `http://localhost:${port}`).pathname);
  const relativePath = pathname === '/' ? 'index.html' : pathname.slice(1);
  const resolved = path.resolve(root, relativePath);
  if (!resolved.startsWith(root)) return null;
  return resolved;
}

const emptyCordova = [
  'window.cordova = window.cordova || {};',
  'window.cordova.platformId = window.cordova.platformId || "browser";',
  'setTimeout(function() { document.dispatchEvent(new Event("deviceready")); }, 0);',
].join('\n');

const emptyPluginList =
  'cordova.define && cordova.define("cordova/plugin_list", function(require, exports, module) { module.exports = []; module.exports.metadata = {}; });';

http
  .createServer((req, res) => {
    if (req.url.startsWith('/cordova.js')) return send(res, 200, emptyCordova, 'text/javascript');
    if (req.url.startsWith('/cordova_plugins.js')) {
      return send(res, 200, emptyPluginList, 'text/javascript');
    }

    const filepath = resolveRequestPath(req.url);
    if (!filepath) return send(res, 403, 'Forbidden');

    fs.readFile(filepath, (err, data) => {
      if (err) return send(res, 404, 'Not found');
      const ext = path.extname(filepath).toLowerCase();
      send(res, 200, data, mimeTypes[ext] || 'application/octet-stream');
    });
  })
  .listen(port, '0.0.0.0', () => {
    console.log(`Serving ${root} at http://127.0.0.1:${port}`);
  });
