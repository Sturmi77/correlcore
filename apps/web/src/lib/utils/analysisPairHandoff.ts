import type { InsightResponse } from '$lib/api/insights';

export type AnalysisSignalKind = 'tag' | 'symptom' | 'work_context' | 'metric' | 'unknown';

export type AnalysisSignalRef = {
  kind: AnalysisSignalKind;
  id: string;
  label?: string;
  metric?: string;
  context?: string;
  lagDays?: number;
};

export type AnalysisPairHandoff = {
  version: 1;
  signals: [AnalysisSignalRef, AnalysisSignalRef];
};

type PayloadRecord = Record<string, unknown>;

function record(value: unknown): PayloadRecord | null {
  return value && typeof value === 'object' && !Array.isArray(value)
    ? (value as PayloadRecord)
    : null;
}

function text(value: unknown): string | null {
  return typeof value === 'string' && value.trim().length > 0 ? value.trim() : null;
}

function number(value: unknown): number | null {
  return typeof value === 'number' && Number.isFinite(value) ? value : null;
}

export function normalizeMetric(metric: string): string {
  if (metric === 'mood' || metric === 'mood_avg') return 'mood_score';
  if (metric === 'energy_avg') return 'energy';
  if (metric === 'stress_avg') return 'stress';
  if (metric === 'sleep_quality_avg') return 'sleep_quality';
  return metric;
}

function normalizedRef(value: unknown): AnalysisSignalRef | null {
  const candidate = record(value);
  if (!candidate) return null;
  const kind = text(candidate.kind);
  const id = text(candidate.id);
  if (!id || !['tag', 'symptom', 'work_context', 'metric', 'unknown'].includes(kind ?? '')) {
    return null;
  }
  const lagDays = number(candidate.lagDays);
  return {
    kind: kind as AnalysisSignalKind,
    id,
    ...(text(candidate.label) ? { label: text(candidate.label)! } : {}),
    ...(text(candidate.metric) ? { metric: normalizeMetric(text(candidate.metric)!) } : {}),
    ...(text(candidate.context) ? { context: text(candidate.context)! } : {}),
    ...(lagDays !== null ? { lagDays } : {}),
  };
}

export function createAnalysisPair(
  first: AnalysisSignalRef,
  second: AnalysisSignalRef
): AnalysisPairHandoff {
  return { version: 1, signals: [first, second] };
}

export function analysisPairQuery(pair: AnalysisPairHandoff): string {
  const params = new URLSearchParams();
  params.set('pair', JSON.stringify(pair));
  return params.toString();
}

export function parseAnalysisPair(params: URLSearchParams): AnalysisPairHandoff | null {
  const raw = params.get('pair');
  if (raw) {
    try {
      const value = record(JSON.parse(raw));
      const signals = Array.isArray(value?.signals) ? value.signals : [];
      const first = normalizedRef(signals[0]);
      const second = normalizedRef(signals[1]);
      if (value?.version === 1 && first && second) return createAnalysisPair(first, second);
    } catch {
      // Fall through to the legacy link below.
    }
  }

  // Compatibility for links emitted before A08. Both ids are still required;
  // the unknown kind deliberately prevents guessing a richer identity.
  const legacy = (params.get('signals') ?? '')
    .split(',')
    .map((id) => id.trim())
    .filter(Boolean);
  return legacy.length === 2
    ? createAnalysisPair({ kind: 'unknown', id: legacy[0] }, { kind: 'unknown', id: legacy[1] })
    : null;
}

function payloadFeatureRef(value: unknown, lagDays?: number): AnalysisSignalRef | null {
  const feature = record(value);
  if (!feature) return null;
  const kind = text(feature.kind);
  if (!kind || !['tag', 'symptom', 'work_context', 'metric'].includes(kind)) return null;
  const rawId = text(feature.id) ?? text(feature.key);
  if (!rawId) return null;
  const id = rawId.replace(/^(tag|symptom|metric|work_context):/, '');
  return {
    kind: kind as Exclude<AnalysisSignalKind, 'unknown'>,
    id: kind === 'metric' ? normalizeMetric(id) : id,
    ...(text(feature.name) ? { label: text(feature.name)! } : {}),
    ...(kind === 'metric' ? { metric: normalizeMetric(id) } : {}),
    ...(kind === 'work_context' ? { context: id } : {}),
    ...(lagDays !== undefined ? { lagDays } : {}),
  };
}

function subjectRef(insight: InsightResponse): AnalysisSignalRef | null {
  const payload = insight.payload ?? {};
  if (insight.subject_type === 'work_context') {
    const context = text(payload.work_context);
    return context
      ? { kind: 'work_context', id: context, context, label: insight.subject_label ?? context }
      : null;
  }
  if (
    (insight.subject_type === 'tag' || insight.subject_type === 'symptom') &&
    insight.subject_id
  ) {
    return {
      kind: insight.subject_type,
      id: insight.subject_id,
      ...(insight.subject_label ? { label: insight.subject_label } : {}),
    };
  }
  if (insight.subject_type === 'metric') {
    const metric = normalizeMetric(insight.subject_id ?? insight.metric);
    return { kind: 'metric', id: metric, metric, label: insight.subject_label ?? metric };
  }
  return null;
}

/** All structured identities that a persisted insight actually proves. */
export function insightSignalRefs(insight: InsightResponse): AnalysisSignalRef[] {
  const payload = insight.payload ?? {};
  const lagDays = number(payload.lag_days) ?? undefined;
  if (payload.method === 'lag') {
    return [
      payloadFeatureRef(payload.feature, lagDays),
      payloadFeatureRef(payload.target, lagDays),
    ].filter((item): item is AnalysisSignalRef => item !== null);
  }
  if (payload.kind === 'symptom_tag_cooccurrence') {
    const symptomId = text(payload.symptom_id);
    const tagId = text(payload.tag_id);
    const compositeRefs: AnalysisSignalRef[] = [];
    if (symptomId) {
      compositeRefs.push({
        kind: 'symptom',
        id: symptomId,
        label: text(payload.symptom_name) ?? undefined,
      });
    }
    if (tagId) {
      compositeRefs.push({
        kind: 'tag',
        id: tagId,
        label: text(payload.tag_name) ?? undefined,
      });
    }
    return compositeRefs;
  }

  const refs: AnalysisSignalRef[] = [];
  const subject = subjectRef(insight);
  if (subject) refs.push(subject);
  const features = Array.isArray(payload.features) ? payload.features : [];
  refs.push(
    ...features
      .map((feature) => payloadFeatureRef(feature))
      .filter((item): item is AnalysisSignalRef => item !== null)
  );
  const metric = normalizeMetric(insight.metric);
  if (!refs.some((ref) => ref.kind === 'metric' && ref.id === metric)) {
    refs.push({ kind: 'metric', id: metric, metric });
  }
  return refs;
}

function refMatches(requested: AnalysisSignalRef, actual: AnalysisSignalRef): boolean {
  if (requested.kind !== 'unknown' && requested.kind !== actual.kind) return false;
  if (requested.id !== actual.id) return false;
  if (
    requested.metric &&
    normalizeMetric(requested.metric) !== normalizeMetric(actual.metric ?? actual.id)
  )
    return false;
  if (requested.context && requested.context !== (actual.context ?? actual.id)) return false;
  if (requested.lagDays !== undefined && requested.lagDays !== actual.lagDays) return false;
  return true;
}

/** Both sides must be present. A match to only one pin is never a pair hit. */
export function insightMatchesAnalysisPair(
  insight: InsightResponse,
  pair: AnalysisPairHandoff
): boolean {
  const refs = insightSignalRefs(insight);
  const [first, second] = pair.signals;
  return refs.some((ref) => refMatches(first, ref)) && refs.some((ref) => refMatches(second, ref));
}

export function partnerForInsight(
  insight: InsightResponse,
  pair: AnalysisPairHandoff
): AnalysisSignalRef | null {
  const refs = insightSignalRefs(insight);
  const [first, second] = pair.signals;
  const firstIsSubject = refs.some((ref) => refMatches(first, ref));
  const secondIsSubject = refs.some((ref) => refMatches(second, ref));
  if (!firstIsSubject || !secondIsSubject) return null;

  const subject = subjectRef(insight) ?? payloadFeatureRef(insight.payload?.feature);
  if (!subject) return second;
  if (refMatches(first, subject)) return second;
  if (refMatches(second, subject)) return first;
  return second;
}
