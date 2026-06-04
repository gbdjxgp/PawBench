import { useEffect, useMemo, useState } from 'react';
import type { TaskRecord } from '@/lib/types';
import { cn, complexityBadgeClass } from '@/lib/utils';
import TaskModal from '@/components/react/TaskModal';

interface Props {
  tasks: TaskRecord[];
  baseUrl: string;
  labels: {
    search: string;
    source: string;
    complexity: string;
    capability: string;
    modality: string;
    environment: string;
    scenario_top: string;
    reset: string;
    empty: string;
    count: string;
    modal: {
      prompt: string;
      expected: string;
      grading: string;
      viewOnGitHub: string;
      close: string;
    };
  };
}

type Filters = {
  q: string;
  source: string | 'all';
  complexity: string | 'all';
  capability: string | 'all';
  modality: string | 'all';
  environment: string | 'all';
  scenario_top: string | 'all';
};

const initial: Filters = {
  q: '',
  source: 'all',
  complexity: 'all',
  capability: 'all',
  modality: 'all',
  environment: 'all',
  scenario_top: 'all',
};

export default function TaskExplorer({ tasks, labels }: Props) {
  const [f, setF] = useState<Filters>(initial);
  const [openId, setOpenId] = useState<string | null>(null);

  const taskById = useMemo(() => {
    const m = new Map<string, TaskRecord>();
    for (const t of tasks) m.set(t.t_id, t);
    return m;
  }, [tasks]);

  // Open modal from URL on mount; sync URL when modal toggles.
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const id = params.get('task');
    if (id && taskById.has(id)) setOpenId(id);

    const onPop = () => {
      const p = new URLSearchParams(window.location.search);
      const next = p.get('task');
      setOpenId(next && taskById.has(next) ? next : null);
    };
    window.addEventListener('popstate', onPop);
    return () => window.removeEventListener('popstate', onPop);
  }, [taskById]);

  const openTask = (id: string) => {
    setOpenId(id);
    const url = new URL(window.location.href);
    url.searchParams.set('task', id);
    window.history.pushState({}, '', url);
  };
  const closeTask = () => {
    setOpenId(null);
    const url = new URL(window.location.href);
    if (url.searchParams.has('task')) {
      url.searchParams.delete('task');
      window.history.pushState({}, '', url);
    }
  };

  const opts = useMemo(() => {
    const sources = new Set<string>();
    const complexity = new Set<string>();
    const caps = new Set<string>();
    const modalities = new Set<string>();
    const environments = new Set<string>();
    const scenarioTops = new Set<string>();
    for (const t of tasks) {
      if (t.source_dataset) sources.add(t.source_dataset);
      if (t.labels?.complexity) complexity.add(t.labels.complexity);
      for (const c of t.labels?.capabilities ?? []) caps.add(c);
      modalities.add(t.labels?.modality?.type || 'text');
      if (t.labels?.environment) environments.add(t.labels.environment);
      const scTop = (t.labels?.scenario || '').split('/', 1)[0];
      if (scTop) scenarioTops.add(scTop);
    }
    const sortStr = (a: string, b: string) => a.localeCompare(b);
    return {
      sources: [...sources].sort(sortStr),
      complexity: [...complexity].sort(sortStr),
      caps: [...caps].sort(sortStr),
      modalities: [...modalities].sort(sortStr),
      environments: [...environments].sort(sortStr),
      scenarioTops: [...scenarioTops].sort(sortStr),
    };
  }, [tasks]);

  const filtered = useMemo(() => {
    const q = f.q.trim().toLowerCase();
    return tasks.filter((t) => {
      if (q && !(t.t_id.toLowerCase().includes(q) || t.name.toLowerCase().includes(q) || (t.task_id || '').toLowerCase().includes(q))) return false;
      if (f.source !== 'all' && t.source_dataset !== f.source) return false;
      if (f.complexity !== 'all' && t.labels?.complexity !== f.complexity) return false;
      if (f.capability !== 'all' && !(t.labels?.capabilities ?? []).includes(f.capability)) return false;
      if (f.modality !== 'all' && (t.labels?.modality?.type || 'text') !== f.modality) return false;
      if (f.environment !== 'all' && t.labels?.environment !== f.environment) return false;
      if (f.scenario_top !== 'all' && (t.labels?.scenario || '').split('/', 1)[0] !== f.scenario_top) return false;
      return true;
    });
  }, [tasks, f]);

  const openTaskRec = openId ? taskById.get(openId) ?? null : null;

  return (
    <>
      <div className="grid grid-cols-12 gap-6">
        <aside className="col-span-12 md:col-span-3 lg:col-span-3 space-y-4 md:sticky md:top-20 md:self-start">
          <div>
            <input
              value={f.q}
              onChange={(e) => setF({ ...f, q: e.target.value })}
              placeholder={labels.search}
              className="w-full px-3 py-2 text-sm rounded-md border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 focus:outline-none focus:ring-2 focus:ring-brand-500"
            />
          </div>
          <FilterGroup label={labels.complexity}   value={f.complexity}   options={opts.complexity}    onChange={(v) => setF({ ...f, complexity: v })} />
          <FilterGroup label={labels.modality}     value={f.modality}     options={opts.modalities}    onChange={(v) => setF({ ...f, modality: v })} />
          <FilterGroup label={labels.environment}  value={f.environment}  options={opts.environments}  onChange={(v) => setF({ ...f, environment: v })} />
          <FilterGroup label={labels.capability}   value={f.capability}   options={opts.caps}          onChange={(v) => setF({ ...f, capability: v })} />
          <FilterGroup label={labels.scenario_top} value={f.scenario_top} options={opts.scenarioTops}  onChange={(v) => setF({ ...f, scenario_top: v })} />
          <FilterGroup label={labels.source}       value={f.source}       options={opts.sources}       onChange={(v) => setF({ ...f, source: v })} />
          <button
            type="button"
            onClick={() => setF(initial)}
            className="text-xs text-slate-500 hover:text-slate-800 dark:hover:text-slate-200 underline-offset-2 hover:underline"
          >
            {labels.reset}
          </button>
        </aside>

        <section className="col-span-12 md:col-span-9 lg:col-span-9 space-y-4">
          <div className="text-xs text-slate-500">
            {labels.count.replace('{count}', String(filtered.length))}
          </div>
          {filtered.length === 0 ? (
            <div className="text-sm text-slate-500 py-8 text-center">{labels.empty}</div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-3">
              {filtered.map((t) => (
                <button
                  key={t.t_id}
                  type="button"
                  onClick={() => openTask(t.t_id)}
                  className="text-left block w-full rounded-lg border border-slate-200 dark:border-slate-800 p-4 hover:border-brand-500 dark:hover:border-brand-500 hover:shadow-sm transition bg-white dark:bg-slate-900 focus:outline-none focus:ring-2 focus:ring-brand-500"
                >
                  <div className="flex items-center gap-2 mb-2">
                    <span className="text-xs font-mono text-slate-500">{t.t_id}</span>
                    {t.labels?.complexity && (
                      <span className={complexityBadgeClass(t.labels.complexity)}>{t.labels.complexity}</span>
                    )}
                    {t.source_dataset && <span className="badge badge-source">{t.source_dataset}</span>}
                  </div>
                  <div className="font-medium text-slate-800 dark:text-slate-100 line-clamp-2 mb-2">{t.name}</div>
                  <div className="flex flex-wrap gap-1">
                    {(t.labels?.capabilities ?? []).slice(0, 3).map((c) => (
                      <span key={c} className="text-[10px] px-1.5 py-0.5 rounded bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400">
                        {c.replace(/_/g, ' ')}
                      </span>
                    ))}
                    {(t.labels?.capabilities?.length ?? 0) > 3 && (
                      <span className="text-[10px] px-1.5 py-0.5 text-slate-500">+{t.labels.capabilities.length - 3}</span>
                    )}
                  </div>
                </button>
              ))}
            </div>
          )}
        </section>
      </div>

      <TaskModal task={openTaskRec} onClose={closeTask} labels={labels.modal} />
    </>
  );
}

function FilterGroup({
  label, value, options, onChange,
}: {
  label: string; value: string; options: string[]; onChange: (v: string) => void;
}) {
  return (
    <div>
      <div className="text-xs font-medium uppercase tracking-wide text-slate-400 mb-1.5">{label}</div>
      <div className="flex flex-wrap gap-1">
        <Chip active={value === 'all'} onClick={() => onChange('all')}>All</Chip>
        {options.map((o) => (
          <Chip key={o} active={value === o} onClick={() => onChange(o)}>{o}</Chip>
        ))}
      </div>
    </div>
  );
}

function Chip({ active, onClick, children }: { active: boolean; onClick: () => void; children: React.ReactNode }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        'px-2 py-0.5 rounded text-xs border transition',
        active
          ? 'bg-brand-700 border-brand-700 text-white'
          : 'border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800'
      )}
    >
      {children}
    </button>
  );
}
