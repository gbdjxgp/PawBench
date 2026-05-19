import { useEffect, useRef } from 'react';
import type { TaskRecord } from '@/lib/types';
import { renderMarkdownLite } from '@/lib/markdown-lite';
import { complexityBadgeClass } from '@/lib/utils';

interface Props {
  task: TaskRecord | null;
  onClose: () => void;
  labels: {
    prompt: string;
    expected: string;
    grading: string;
    viewOnGitHub: string;
    close: string;
  };
}

export default function TaskModal({ task, onClose, labels }: Props) {
  const dialogRef = useRef<HTMLDivElement>(null);

  // Lock scroll, handle Escape, focus the dialog.
  useEffect(() => {
    if (!task) return;
    const prev = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose(); };
    window.addEventListener('keydown', onKey);
    requestAnimationFrame(() => dialogRef.current?.focus());
    return () => {
      document.body.style.overflow = prev;
      window.removeEventListener('keydown', onKey);
    };
  }, [task, onClose]);

  if (!task) return null;

  const sec = task.sections || {};
  const promptHtml   = sec.prompt           ? renderMarkdownLite(sec.prompt)           : '';
  const expectedHtml = sec.expected         ? renderMarkdownLite(sec.expected)         : '';
  const gradingHtml  = sec.grading_criteria ? renderMarkdownLite(sec.grading_criteria) : '';

  const ghUrl = `https://github.com/agentscope-ai/pawbench/blob/main/${task.source_path}`;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label={task.name}
      className="fixed inset-0 z-50 flex items-center justify-center p-2 sm:p-6"
    >
      <button
        type="button"
        aria-label={labels.close}
        onClick={onClose}
        className="absolute inset-0 bg-slate-950/60 backdrop-blur-sm cursor-default"
      />
      <div
        ref={dialogRef}
        tabIndex={-1}
        className="relative w-full max-w-3xl max-h-[92vh] flex flex-col rounded-xl bg-white dark:bg-slate-950 shadow-2xl border border-slate-200 dark:border-slate-800 outline-none"
      >
        {/* Header */}
        <div className="px-5 py-4 border-b border-slate-200 dark:border-slate-800 flex items-start gap-4">
          <div className="flex-1 min-w-0">
            <div className="flex flex-wrap items-center gap-1.5 text-xs mb-1.5">
              <span className="font-mono text-slate-500">{task.t_id}</span>
              {task.labels?.complexity && (
                <span className={complexityBadgeClass(task.labels.complexity)}>{task.labels.complexity}</span>
              )}
              {task.source_dataset && <span className="badge badge-source">{task.source_dataset}</span>}
              {task.grading_type && (
                <span className="badge bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300">
                  {task.grading_type}
                </span>
              )}
            </div>
            <h2 className="text-lg sm:text-xl font-bold text-slate-900 dark:text-white truncate">
              {task.name}
            </h2>
          </div>
          <button
            type="button"
            aria-label={labels.close}
            onClick={onClose}
            className="shrink-0 -mr-1 p-2 rounded-md text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 hover:text-slate-700 dark:hover:text-slate-200"
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M18 6L6 18M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Scrollable body with three colored sections */}
        <div className="flex-1 overflow-y-auto p-4 sm:p-5 space-y-4 bg-slate-50/40 dark:bg-slate-900/30">
          {promptHtml && (
            <Section
              title={labels.prompt}
              tone="sky"
              html={promptHtml}
            />
          )}
          {expectedHtml && (
            <Section
              title={labels.expected}
              tone="emerald"
              html={expectedHtml}
            />
          )}
          {gradingHtml && (
            <Section
              title={labels.grading}
              tone="amber"
              html={gradingHtml}
            />
          )}
          {!promptHtml && !expectedHtml && !gradingHtml && (
            <div className="text-sm text-slate-500 text-center py-12">
              No content for this task.
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-5 py-3 border-t border-slate-200 dark:border-slate-800 flex items-center justify-between gap-3 bg-white dark:bg-slate-950">
          <a
            href={ghUrl}
            target="_blank"
            rel="noopener"
            className="text-xs text-slate-500 hover:text-brand-700 dark:hover:text-brand-300 inline-flex items-center gap-1"
          >
            {labels.viewOnGitHub} ↗
          </a>
          <button
            type="button"
            onClick={onClose}
            className="px-3 py-1.5 rounded-md text-xs border border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800"
          >
            {labels.close}
          </button>
        </div>
      </div>
    </div>
  );
}

interface SectionProps {
  title: string;
  tone: 'sky' | 'emerald' | 'amber';
  html: string;
}

const TONES: Record<SectionProps['tone'], { bg: string; ring: string; pill: string }> = {
  sky: {
    bg:   'bg-sky-50 dark:bg-sky-950/40',
    ring: 'border-sky-200 dark:border-sky-900',
    pill: 'bg-sky-200 dark:bg-sky-900 text-sky-900 dark:text-sky-100',
  },
  emerald: {
    bg:   'bg-emerald-50 dark:bg-emerald-950/40',
    ring: 'border-emerald-200 dark:border-emerald-900',
    pill: 'bg-emerald-200 dark:bg-emerald-900 text-emerald-900 dark:text-emerald-100',
  },
  amber: {
    bg:   'bg-amber-50 dark:bg-amber-950/40',
    ring: 'border-amber-200 dark:border-amber-900',
    pill: 'bg-amber-200 dark:bg-amber-900 text-amber-900 dark:text-amber-100',
  },
};

function Section({ title, tone, html }: SectionProps) {
  const t = TONES[tone];
  return (
    <section className={`rounded-lg border ${t.ring} ${t.bg} p-4`}>
      <div className="flex items-center gap-2 mb-3">
        <span className={`text-[10px] font-semibold uppercase tracking-wider px-1.5 py-0.5 rounded ${t.pill}`}>
          {title}
        </span>
      </div>
      <div className="md-body text-sm text-slate-700 dark:text-slate-200" dangerouslySetInnerHTML={{ __html: html }} />
    </section>
  );
}
