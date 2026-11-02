// 把 project/manual 下的四份正文同步成站点内容（只读镜像，禁止在这里改内容）
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const SITE = path.resolve(HERE, "..");
const MANUAL = path.resolve(SITE, "..");
const OUT = path.join(SITE, "content");

const SRC = [
  { file: "01-第0章-前置.md", slug: "00", title: "第 0 章 · 前置", desc: "gstack、纪律与自检" },
  { file: "02-第一篇.md", slug: "01", title: "第一篇 · 走一遍八环", desc: "A 观察 / B 复现 / C 白手起家" },
  { file: "03-第二篇.md", slug: "02", title: "第二篇 · 做一个 AI 应用", desc: "判型 → 卡一实操 → 卡二卡三 → 诚实清单" },
  { file: "04-第三篇.md", slug: "03", title: "第三篇 · 搬回自己的课题", desc: "判型 / 瘦身 / 造数 / 红线 / Day-2 / 交卷" }
];

fs.mkdirSync(OUT, { recursive: true });
if (!fs.existsSync(path.join(MANUAL, SRC[0].file))) {
  console.log("未找到上游正文源（CI 环境正常），保留已入库的 content/ 镜像");
  process.exit(0);
}

let n = 0;
for (const s of SRC) {
  const src = path.join(MANUAL, s.file);
  if (!fs.existsSync(src)) {
    console.warn("缺失内容源:", src);
    continue;
  }
  let body = fs.readFileSync(src, "utf8").replace(/\r\n/g, "\n");
  // 去掉原文件的一级标题与顶部元信息引用块，标题由页面布局提供
  body = body.replace(/^# .*\n/, "");
  body = body.replace(/^(?:>.*\n)+\n?/m, "");
  const front = `---\nslug: "${s.slug}"\ntitle: "${s.title}"\ndesc: "${s.desc}"\nsource: "${s.file}"\n---\n\n`;
  fs.writeFileSync(path.join(OUT, `${s.slug}.md`), front + body, "utf8");
  n++;
}
console.log(`同步 ${n} 份正文 -> content/`);

// 图：从 export/figs 复制 SVG 到 public/figs
const FIG_SRC = path.join(MANUAL, "export", "figs");
const FIG_DST = path.join(SITE, "public", "figs");
fs.mkdirSync(FIG_DST, { recursive: true });
let figs = 0;
if (fs.existsSync(FIG_SRC)) {
  for (const f of fs.readdirSync(FIG_SRC)) {
    if (f.endsWith(".svg")) {
      fs.copyFileSync(path.join(FIG_SRC, f), path.join(FIG_DST, f));
      figs++;
    }
  }
}
console.log(`同步 ${figs} 张 SVG -> public/figs/`);
