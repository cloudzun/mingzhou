// 本地验收用的静态服务器：把 dist 挂到 /mingzhou/ 前缀下。
// 为什么需要它：站点 base 是 /mingzhou，直接 `serve dist` 挂根目录会让所有带 BASE 的链接 404，
// 而 qa_pages.py local 是直接读文件、发现不了这个问题——必须起一个"带前缀"的服务再上浏览器。
//
// 用法：node scripts/serve-dist.cjs [port]
// 然后：python scripts/qa_pages.py browser http://127.0.0.1:4321/mingzhou
const http = require("http");
const fs = require("fs");
const path = require("path");

const ROOT = path.resolve(__dirname, "..", "dist");
const PREFIX = "/mingzhou";
const PORT = Number(process.argv[2] || 4321);

const MIME = {
  ".html": "text/html; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".mjs": "text/javascript; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".svg": "image/svg+xml",
  ".png": "image/png",
  ".jpg": "image/jpeg",
  ".woff2": "font/woff2",
  ".wasm": "application/wasm",
  ".webp": "image/webp",
  ".ico": "image/x-icon",
  ".txt": "text/plain; charset=utf-8",
};

http
  .createServer((req, res) => {
    const u = decodeURIComponent(req.url.split("?")[0]);
    if (u !== PREFIX && !u.startsWith(PREFIX + "/")) {
      res.writeHead(404, { "Content-Type": "text/plain; charset=utf-8" });
      return res.end("outside base: " + u);
    }
    let p = path.join(ROOT, u.slice(PREFIX.length));
    if (p.endsWith(path.sep) || p === ROOT) p = path.join(p, "index.html");
    fs.readFile(p, (e, d) => {
      if (e) {
        res.writeHead(404, { "Content-Type": "text/plain; charset=utf-8" });
        return res.end("404 " + u);
      }
      res.writeHead(200, { "Content-Type": MIME[path.extname(p).toLowerCase()] || "application/octet-stream" });
      res.end(d);
    });
  })
  .listen(PORT, () => console.log(`serving ${ROOT} at http://127.0.0.1:${PORT}${PREFIX}/`));
