(() => {
  "use strict";

  const round = (value) => Math.round(value * 100) / 100;
  const visible = (element) => {
    const style = getComputedStyle(element);
    const rect = element.getBoundingClientRect();
    return style.display !== "none" && style.visibility !== "hidden" && Number(style.opacity) !== 0 && rect.width > 0 && rect.height > 0;
  };
  const cssPath = (element) => {
    if (element.id) return `#${CSS.escape(element.id)}`;
    const parts = [];
    let current = element;
    while (current && current.nodeType === Node.ELEMENT_NODE && parts.length < 5) {
      let part = current.tagName.toLowerCase();
      if (current.classList.length) part += `.${[...current.classList].slice(0, 2).map((name) => CSS.escape(name)).join(".")}`;
      const parent = current.parentElement;
      if (parent) {
        const siblings = [...parent.children].filter((item) => item.tagName === current.tagName);
        if (siblings.length > 1) part += `:nth-of-type(${siblings.indexOf(current) + 1})`;
      }
      parts.unshift(part);
      current = parent;
    }
    return parts.join(" > ");
  };
  const roleFor = (element) => {
    if (element.dataset.typographyRole) return element.dataset.typographyRole;
    if (/^H[1-6]$/.test(element.tagName)) return "headline";
    if (element.matches("p, dd, .status-note, .structure-note")) return "body";
    return "label";
  };
  const defaultMaxLines = (role) => role === "headline" ? 3 : role === "body" ? 5 : 3;

  const logicalCharacters = (element) => {
    const items = [];
    const visit = (node) => {
      if (node.nodeType === Node.TEXT_NODE) {
        const value = node.nodeValue || "";
        for (let index = 0; index < value.length; index += 1) {
          const char = value[index];
          const range = document.createRange();
          range.setStart(node, index);
          range.setEnd(node, index + 1);
          const rects = [...range.getClientRects()].filter((rect) => rect.width || rect.height);
          const rect = rects[0];
          items.push({
            kind: "character",
            char,
            rect: rect ? {left: rect.left, right: rect.right, top: rect.top, bottom: rect.bottom, width: rect.width} : null,
          });
        }
        return;
      }
      if (node.nodeType !== Node.ELEMENT_NODE) return;
      if (node.tagName === "BR") {
        items.push({kind: "forced-break"});
        return;
      }
      for (const child of node.childNodes) visit(child);
    };
    for (const child of element.childNodes) visit(child);
    return items;
  };

  const renderedLines = (element) => {
    const items = logicalCharacters(element);
    const buckets = [];
    for (let index = 0; index < items.length; index += 1) {
      const item = items[index];
      if (item.kind !== "character" || !item.rect || !item.char.trim()) continue;
      let line = buckets.find((candidate) => Math.abs(candidate.top - item.rect.top) <= 2);
      if (!line) {
        line = {top: item.rect.top, bottom: item.rect.bottom, left: item.rect.left, right: item.rect.right, characters: []};
        buckets.push(line);
      }
      line.top = Math.min(line.top, item.rect.top);
      line.bottom = Math.max(line.bottom, item.rect.bottom);
      line.left = Math.min(line.left, item.rect.left);
      line.right = Math.max(line.right, item.rect.right);
      line.characters.push({index, char: item.char, left: item.rect.left});
    }
    buckets.sort((a, b) => a.top - b.top || a.left - b.left);
    for (const line of buckets) line.characters.sort((a, b) => a.left - b.left);

    const lines = buckets.map((line) => ({
      text: line.characters.map((item) => item.char).join("").trim(),
      top: round(line.top),
      bottom: round(line.bottom),
      width: round(line.right - line.left),
      first_index: Math.min(...line.characters.map((item) => item.index)),
      last_index: Math.max(...line.characters.map((item) => item.index)),
    }));
    const midTokenBreaks = [];
    for (let index = 1; index < lines.length; index += 1) {
      const previous = lines[index - 1];
      const current = lines[index];
      const between = items.slice(previous.last_index + 1, current.first_index);
      const hasSeparator = between.some((item) => item.kind === "forced-break" || (item.kind === "character" && /\s/.test(item.char)));
      const previousChar = previous.text.slice(-1);
      const currentChar = current.text.slice(0, 1);
      if (!hasSeparator && /[0-9A-Za-z가-힣]/.test(previousChar) && /[0-9A-Za-z가-힣]/.test(currentChar)) {
        midTokenBreaks.push(`${previousChar}|${currentChar}`);
      }
    }
    return {lines, mid_token_breaks: midTokenBreaks};
  };

  const collect = () => {
    const candidates = [...document.querySelectorAll([
      "[data-typography]",
      "h1",
      "h2",
      ".hero-copy .lead",
      ".module-copy > p:not(.module-index):not(.concept-label)",
      ".closing-copy > p:not(.eyebrow)",
      "figcaption",
      ".caution",
      ".status-note-text",
      ".structure-note p",
      ".number-pair span",
      ".spec-table dd",
    ].join(","))].filter(visible);
    const elements = candidates.map((element) => {
      const rect = element.getBoundingClientRect();
      const style = getComputedStyle(element);
      const role = roleFor(element);
      const rendered = renderedLines(element);
      return {
        selector: cssPath(element),
        role,
        text: element.innerText.trim(),
        rect: {left: round(rect.left), right: round(rect.right), top: round(rect.top), bottom: round(rect.bottom)},
        client_width: round(element.clientWidth),
        scroll_width: round(element.scrollWidth),
        font_size: round(parseFloat(style.fontSize)),
        line_height: round(parseFloat(style.lineHeight) || parseFloat(style.fontSize) * 1.2),
        max_lines: Number(element.getAttribute("data-typography-max-lines") || defaultMaxLines(role)),
        allow_short_last_line: element.getAttribute("data-typography-allow-short-last") === "true",
        lines: rendered.lines,
        mid_token_breaks: rendered.mid_token_breaks,
      };
    });
    return {
      schema_version: "1.0",
      page: location.href,
      captured_at: new Date().toISOString(),
      width: innerWidth,
      height: innerHeight,
      document: {
        client_width: document.documentElement.clientWidth,
        scroll_width: document.documentElement.scrollWidth,
        scroll_height: document.documentElement.scrollHeight,
      },
      elements,
    };
  };

  window.__collectTypographyMetrics = collect;
  return collect();
})();
