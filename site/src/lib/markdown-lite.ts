/**
 * Synchronous, dependency-free Markdown-to-HTML renderer for in-browser use
 * (the modal preview on /tasks). Handles the subset of Markdown we expect in
 * task ``Prompt`` / ``Expected Behavior`` / ``Grading Criteria`` sections —
 * paragraphs, headings, bold/italic/inline-code, ordered & unordered lists,
 * fenced code blocks (rendered as plain `<pre><code>`).
 *
 * Not a spec-compliant CommonMark implementation — intentionally tiny to keep
 * the React island bundle small. Use ``renderTaskMarkdown`` (markdown.ts) on
 * the server side when shiki highlighting matters.
 */

const ESCAPE_MAP: Record<string, string> = { '&': '&amp;', '<': '&lt;', '>': '&gt;' };

export function escapeHtml(s: string): string {
  return s.replace(/[&<>]/g, (c) => ESCAPE_MAP[c] || c);
}

function inline(s: string): string {
  return escapeHtml(s)
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
    .replace(/(?<!\*)\*([^*]+)\*(?!\*)/g, '<em>$1</em>');
}

export function renderMarkdownLite(md: string): string {
  if (!md) return '';
  const out: string[] = [];
  const lines = md.split('\n');
  let i = 0;
  let inList: 'ul' | 'ol' | null = null;
  const flushList = () => { if (inList) { out.push(`</${inList}>`); inList = null; } };

  while (i < lines.length) {
    const ln = lines[i];

    if (ln.startsWith('```')) {
      flushList();
      const lang = ln.slice(3).trim();
      const buf: string[] = [];
      i++;
      while (i < lines.length && !lines[i].startsWith('```')) { buf.push(lines[i]); i++; }
      i++;
      out.push(
        `<pre class="md-code"${lang ? ` data-lang="${escapeHtml(lang)}"` : ''}><code>${escapeHtml(buf.join('\n'))}</code></pre>`
      );
      continue;
    }

    const h3 = ln.match(/^###\s+(.*)$/);
    const h2 = ln.match(/^##\s+(.*)$/);
    const h1 = ln.match(/^#\s+(.*)$/);
    if (h3) { flushList(); out.push(`<h4>${inline(h3[1])}</h4>`); i++; continue; }
    if (h2) { flushList(); out.push(`<h3>${inline(h2[1])}</h3>`); i++; continue; }
    if (h1) { flushList(); out.push(`<h2>${inline(h1[1])}</h2>`); i++; continue; }

    const ul = ln.match(/^\s*[-*]\s+(.*)$/);
    const ol = ln.match(/^\s*\d+\.\s+(.*)$/);
    if (ul || ol) {
      const want = ul ? 'ul' : 'ol';
      if (inList !== want) { flushList(); out.push(`<${want}>`); inList = want; }
      out.push(`<li>${inline((ul || ol)![1])}</li>`);
      i++; continue;
    }

    if (ln.trim() === '') { flushList(); i++; continue; }

    flushList();
    out.push(`<p>${inline(ln)}</p>`);
    i++;
  }
  flushList();
  return out.join('\n');
}
