// 内容加载器：在构建期读 content/*.md，供 getStaticPaths 与页面渲染共用。
// 单独成模块的原因：Astro 会把 getStaticPaths 提升，模块内声明的变量/函数在那里取不到。
import fs from "node:fs";
import { marked } from "marked";
import path from "node:path";

const SITE = path.resolve(process.cwd());
const CONTENT = path.join(SITE, "content");

function parseFront(raw) {
  const m = raw.match(/^---\n([\s\S]*?)\n---\n([\s\S]*)$/);
  if (!m) return { meta: {}, body: raw };
  const meta = {};
  for (const line of m[1].split("\n")) {
    const i = line.indexOf(":");
    if (i > 0) meta[line.slice(0, i).trim()] = line.slice(i + 1).trim().replace(/^"|"$/g, "");
  }
  return { meta, body: m[2] };
}

export function loadDocs() {
  if (!fs.existsSync(CONTENT)) return [];
  return fs
    .readdirSync(CONTENT)
    .filter((f) => f.endsWith(".md"))
    .map((f) => {
      const { meta, body } = parseFront(fs.readFileSync(path.join(CONTENT, f), "utf8"));
      return { ...meta, body, slug: meta.slug || path.basename(f, ".md") };
    })
    .sort((a, b) => a.slug.localeCompare(b.slug));
}

export function inlineFig(id) {
  const p = path.join(SITE, "public", "figs", `fig-${id}.svg`);
  if (!fs.existsSync(p)) return `<p class="missing">[缺图 ${id}]</p>`;
  const svg = fs.readFileSync(p, "utf8").replace(/<svg([^>]*)>/, (_s, attrs) => {
    const cleaned = attrs.replace(/\s(width|height)="[^"]*"/g, "");
    return `<svg${cleaned} id="fig-${id}" role="img" aria-label="图 ${id}">`;
  });
  return `<figure class="fig">${svg}</figure>`;
}


const FIG_BLOCK = /```mermaid\n[\s\S]*?```\s*\n+(\*图 (\d-\d)[：:][^*]*\*)/g;

export function render(md) {
  md = md.replace(/\r\n/g, "\n");
  const figs = [];
  md = md.replace(FIG_BLOCK, (_m, cap, id) => {
    figs.push(id);
    return '\n\n@@FIG_' + id + '@@\n\n' + cap + '\n';
  });
  let html = marked.parse(md, { mangle: false });
  figs.forEach((id) => {
    html = html.replace('<p>@@FIG_' + id + '@@</p>', inlineFig(id));
  });
  html = html.replace(/<h([23])>([\s\S]*?)<\/h\1>/g, (_m, lvl, text) => {
    const plain = text.replace(/<[^>]+>/g, '');
    const id = 'h-' + plain.trim().replace(/[^\u4e00-\u9fa5A-Za-z0-9]+/g, '-').slice(0, 40);
    return '<h' + lvl + ' id="' + id + '">' + text + '</h' + lvl + '>';
  });
  return { html, figs };
}
