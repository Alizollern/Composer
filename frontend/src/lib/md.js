// Компактный markdown -> HTML (без внешних зависимостей).
function esc(s) {
  return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}
function inline(s) {
  s = esc(s);
  s = s.replace(/\[([^\]]+)\]\((https?:\/\/[^)\s]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>');
  s = s.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
  s = s.replace(/(^|[^*])\*([^*\n]+)\*/g, "$1<em>$2</em>");
  s = s.replace(/`([^`]+)`/g, "<code>$1</code>");
  s = s.replace(/(^|[\s(])((https?:\/\/[^\s<)]+))/g, '$1<a href="$2" target="_blank" rel="noopener">$2</a>');
  return s;
}

export function renderMd(md) {
  if (!md) return "";
  const lines = md.replace(/\r/g, "").split("\n");
  const out = [];
  let i = 0;
  let listType = null;
  const closeList = () => { if (listType) { out.push(listType === "ol" ? "</ol>" : "</ul>"); listType = null; } };

  while (i < lines.length) {
    const line = lines[i];

    if (/^```/.test(line)) {
      closeList();
      const buf = [];
      i++;
      while (i < lines.length && !/^```/.test(lines[i])) { buf.push(lines[i]); i++; }
      i++;
      out.push("<pre><code>" + esc(buf.join("\n")) + "</code></pre>");
      continue;
    }
    if (line.includes("|") && i + 1 < lines.length &&
        /^\s*\|?[\s:|-]+\|[\s:|-]*$/.test(lines[i + 1]) && lines[i + 1].includes("-")) {
      closeList();
      const split = (r) => r.replace(/^\s*\|/, "").replace(/\|\s*$/, "").split("|").map((c) => c.trim());
      const head = split(line);
      i += 2;
      const body = [];
      while (i < lines.length && lines[i].includes("|")) { body.push(split(lines[i])); i++; }
      let t = "<table><thead><tr>" + head.map((c) => "<th>" + inline(c) + "</th>").join("") + "</tr></thead><tbody>";
      for (const row of body) t += "<tr>" + row.map((c) => "<td>" + inline(c) + "</td>").join("") + "</tr>";
      out.push(t + "</tbody></table>");
      continue;
    }
    let m = /^(#{1,6})\s+(.*)$/.exec(line);
    if (m) { closeList(); const lvl = Math.min(m[1].length, 4); out.push(`<h${lvl}>${inline(m[2])}</h${lvl}>`); i++; continue; }
    if (/^(\s*[-*_]){3,}\s*$/.test(line)) { closeList(); out.push("<hr/>"); i++; continue; }
    if (/^>\s?/.test(line)) {
      closeList();
      const buf = [];
      while (i < lines.length && /^>\s?/.test(lines[i])) { buf.push(lines[i].replace(/^>\s?/, "")); i++; }
      out.push("<blockquote>" + inline(buf.join(" ")) + "</blockquote>");
      continue;
    }
    if (/^\s*\d+[.)]\s+/.test(line)) {
      if (listType !== "ol") { closeList(); out.push("<ol>"); listType = "ol"; }
      out.push("<li>" + inline(line.replace(/^\s*\d+[.)]\s+/, "")) + "</li>"); i++; continue;
    }
    if (/^\s*[-*+]\s+/.test(line)) {
      if (listType !== "ul") { closeList(); out.push("<ul>"); listType = "ul"; }
      out.push("<li>" + inline(line.replace(/^\s*[-*+]\s+/, "")) + "</li>"); i++; continue;
    }
    if (/^\s*$/.test(line)) { closeList(); i++; continue; }
    closeList();
    const buf = [line];
    i++;
    while (i < lines.length && !/^\s*$/.test(lines[i]) &&
           !/^(#{1,6}\s|>|\s*[-*+]\s|\s*\d+[.)]\s|```)/.test(lines[i])) { buf.push(lines[i]); i++; }
    out.push("<p>" + inline(buf.join(" ")) + "</p>");
  }
  closeList();
  return out.join("\n");
}
