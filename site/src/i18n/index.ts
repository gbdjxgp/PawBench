import zh from './zh.json';
import en from './en.json';

export type Locale = 'zh' | 'en';

const dictionaries: Record<Locale, Record<string, string>> = { zh, en };

export const locales: Locale[] = ['zh', 'en'];

/**
 * Astro/Vite injects the configured ``base`` (e.g. ``/pawbench/``) here at
 * build time. Falls back to ``/`` for non-Astro contexts.
 */
const BASE: string = (
  (typeof import.meta !== 'undefined' && (import.meta as { env?: { BASE_URL?: string } }).env?.BASE_URL) ?? '/'
);

/**
 * Prefix an internal path with the configured base URL.
 *
 * The base ``/pawbench/`` is kept *with* its trailing slash for the root
 * (Astro's dev server only serves the index at ``/pawbench/``, not at
 * ``/pawbench``). Sub-paths drop trailing slashes for stable URLs.
 */
export function withBase(path: string): string {
  const base = BASE.endsWith('/') ? BASE : `${BASE}/`;
  const clean = (path ?? '').replace(/^\/+/, '').replace(/\/+$/, '');
  if (clean === '') return base; // e.g. '/pawbench/'
  return `${base}${clean}`;
}

export function getLocaleFromUrl(url: URL): Locale {
  const baseStripped = url.pathname.replace(BASE.replace(/\/$/, ''), '');
  const seg = baseStripped.split('/').filter(Boolean);
  if (seg[0] === 'en') return 'en';
  return 'zh';
}

export function t(locale: Locale, key: string, vars?: Record<string, string | number>): string {
  const dict = dictionaries[locale] ?? dictionaries.zh;
  let s = dict[key] ?? key;
  if (vars) {
    for (const [k, v] of Object.entries(vars)) {
      s = s.replace(new RegExp(`\\{${k}\\}`, 'g'), String(v));
    }
  }
  return s;
}

/**
 * Build a fully-qualified path for the given locale, including the configured
 * base URL. Examples (with base ``/pawbench/``):
 *   localizedPath('zh', '/')      -> '/pawbench'
 *   localizedPath('zh', '/slice') -> '/pawbench/slice'
 *   localizedPath('en', '/slice') -> '/pawbench/en/slice'
 */
export function localizedPath(locale: Locale, path: string): string {
  const clean = path.startsWith('/') ? path.slice(1) : path;
  const localePart = locale === 'en' ? 'en' : '';
  const joined = [localePart, clean].filter(Boolean).join('/');
  return withBase(joined);
}

export function altLocale(locale: Locale): Locale {
  return locale === 'zh' ? 'en' : 'zh';
}

/**
 * Compute the path to the same page in the *other* locale. ``pathname`` is the
 * current page path with the base already stripped (e.g. ``/slice`` or ``/en/slice``).
 */
export function altLocalePath(locale: Locale, pathname: string): string {
  const other = altLocale(locale);
  let rest = pathname || '/';
  if (locale === 'en') {
    rest = rest.replace(/^\/en(\/|$)/, '/');
  }
  if (other === 'en') {
    const tail = rest === '/' ? '' : rest;
    return withBase(`/en${tail}`);
  }
  return withBase(rest);
}
