// Нарезка текста стандарта на короткие карточки для микро-обучения.
//
// Регламенты в Evergreen обычно структурированы по разделам («1. Заморозка…»,
// «2. Продление…») с подпунктами («1.1.», «1.2.»). Удобная карточка = один
// раздел с его подпунктами: получается 4–6 карточек на стандарт — ровно под
// свайп. Если нумерации нет — режем по абзацам, ограничивая размер карточки.

const SECTION_RE = /^\s*\d+\.\s+\S/;       // «1. Заголовок раздела»
const SUBPOINT_RE = /^\s*\d+\.\d+/;        // «1.1.» — это подпункт, не раздел

function chunkByParagraphs(title, raw) {
  // Запасной вариант: бьём по пустым строкам, склеивая мелкие абзацы так,
  // чтобы на карточке было не больше ~70 слов (иначе это уже не «микро»).
  const paras = raw.split(/\n\s*\n/).map((p) => p.trim()).filter(Boolean);
  const cards = [];
  let buf = [];
  let words = 0;
  for (const p of paras) {
    const w = p.split(/\s+/).length;
    if (words + w > 70 && buf.length) {
      cards.push({ heading: "", body: buf.slice() });
      buf = [];
      words = 0;
    }
    buf.push(p);
    words += w;
  }
  if (buf.length) cards.push({ heading: "", body: buf.slice() });
  if (cards.length === 0) cards.push({ heading: "", body: [raw.trim()] });
  // Первая карточка получает заголовок документа.
  cards[0] = { heading: title, body: cards[0].body };
  return cards;
}

export function splitIntoCards(title, content) {
  const raw = (content || "").replace(/\r/g, "").trim();
  if (!raw) return [{ heading: title, body: ["(пустой стандарт)"] }];

  const lines = raw.split("\n");
  const sections = [];
  let cur = null;
  const intro = [];

  for (const line of lines) {
    const isSection = SECTION_RE.test(line) && !SUBPOINT_RE.test(line);
    if (isSection) {
      if (cur) sections.push(cur);
      cur = { heading: line.trim().replace(/\.\s*$/, ""), body: [] };
    } else if (cur) {
      if (line.trim()) cur.body.push(line.trim());
    } else if (line.trim()) {
      intro.push(line.trim());
    }
  }
  if (cur) sections.push(cur);

  // Нет разделов — уходим в запасную нарезку по абзацам.
  if (sections.length === 0) return chunkByParagraphs(title, raw);

  const cards = [];
  // Вступительная карточка: заголовок документа + преамбула (если есть).
  cards.push({ heading: title, body: intro.length ? intro : ["Пройдём по пунктам стандарта."] });
  cards.push(...sections);
  return cards;
}
