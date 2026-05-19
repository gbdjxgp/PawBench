import { codeToHtml } from 'shiki';

const ESCAPE_MAP: Record<string, string> = { '&': '&amp;', '<': '&lt;', '>': '&gt;' };

function escape(s: string): string {
  return s.replace(/[&<>]/g, (c) => ESCAPE_MAP[c] || c);
}

function inline(s: string): string {
  return escape(s)
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
    .replace(/(?<!\*)\*([^*]+)\*(?!\*)/g, '<em>$1</em>');
}

interface CodeBlock {
  lang: string;
  code: string;
  placeholder: string;
}

/**
 * Render task-section markdown to HTML with shiki-highlighted code blocks.
 *
 * We render fenced code blocks with shiki up-front (it returns HTML), insert
 * placeholders during the markdown pass, then swap them in. shiki is async,
 * so this whole function is async — call it from Astro frontmatter.
 */
export async function renderTaskMarkdown(md: string): Promise<string> {
  if (!md) return '';

  // 1. Extract fenced code blocks first.
  const blocks: CodeBlock[] = [];
  const stripped = md.replace(/```([^\n]*)\n([\s\S]*?)```/g, (_m, lang, code) => {
    const idx = blocks.length;
    blocks.push({
      lang: (lang || '').trim() || 'text',
      code: String(code).replace(/\n$/, ''),
      placeholder: `__PAWBENCH_CODE_${idx}__`,
    });
    return `\n${blocks[idx].placeholder}\n`;
  });

  // 2. Convert each code block via shiki (parallel).
  const rendered = await Promise.all(
    blocks.map(async (b) => {
      const lang = normalizeLang(b.lang);
      try {
        return {
          ...b,
          html: await codeToHtml(b.code, {
            lang,
            themes: { light: 'github-light', dark: 'github-dark' },
            defaultColor: false,
          }),
        };
      } catch {
        return {
          ...b,
          html: `<pre class="shiki-fallback"><code>${escape(b.code)}</code></pre>`,
        };
      }
    })
  );

  // 3. Walk lines, building HTML for prose; swap placeholders.
  const out: string[] = [];
  const lines = stripped.split('\n');
  let i = 0;
  let inList: 'ul' | 'ol' | null = null;
  const flushList = () => { if (inList) { out.push(`</${inList}>`); inList = null; } };

  while (i < lines.length) {
    const ln = lines[i];

    const placeholderMatch = ln.match(/^__PAWBENCH_CODE_(\d+)__$/);
    if (placeholderMatch) {
      flushList();
      const idx = Number(placeholderMatch[1]);
      out.push(rendered[idx]?.html || '');
      i++; continue;
    }

    const h3 = ln.match(/^###\s+(.*)$/);
    const h2 = ln.match(/^##\s+(.*)$/);
    if (h3) { flushList(); out.push(`<h3>${inline(h3[1])}</h3>`); i++; continue; }
    if (h2) { flushList(); out.push(`<h2>${inline(h2[1])}</h2>`); i++; continue; }

    const ul = ln.match(/^\s*[-*]\s+(.*)$/);
    const ol = ln.match(/^\s*\d+\.\s+(.*)$/);
    if (ul || ol) {
      const wantList = ul ? 'ul' : 'ol';
      if (inList !== wantList) { flushList(); out.push(`<${wantList}>`); inList = wantList; }
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

function normalizeLang(lang: string): string {
  const l = lang.toLowerCase();
  if (l === 'py') return 'python';
  if (l === 'sh' || l === 'shell') return 'bash';
  if (l === 'yml') return 'yaml';
  if (l === 'js') return 'javascript';
  if (l === 'ts') return 'typescript';
  if (l === '') return 'text';
  return l;
}
