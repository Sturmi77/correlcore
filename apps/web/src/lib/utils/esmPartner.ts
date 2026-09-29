/**
 * ESM partner glyph (#909 / ADR-0035 addendum).
 *
 * At most one second subject B overlaid on Event-Aligned Small Multiples
 * windows (align stays Event A). Default B from co-occurrence ranks; presence
 * dates come from already-loaded heatmaps — no Dual-Align, no new engine.
 */

import type {
  InsightResponse,
  SymptomTagCooccurrenceCell,
  TagCooccurrencePair,
} from '$lib/api/insights';
import type { SymptomHeatmapResponse, TagHeatmapResponse } from '$lib/api/stats';
import type { WorkContextHeatmapResponse } from '$lib/utils/workContextHeatmap';
import { lagFeature, lagFeatureKind } from '$lib/utils/exploreEventWindows';
import { SMALL_MULTIPLES_RADIUS } from '$lib/components/trends/smallMultiplesGate';

/** Hard budget: one partner overlay (mobile / ~3-panel). */
export const MAX_ESM_PARTNERS = 1;

/** How many ranked candidates to offer in the override control. */
export const ESM_PARTNER_CANDIDATE_LIMIT = 5;

export type EsmPartnerKind = 'tag' | 'symptom' | 'work_context';

export type EsmPartner = {
  id: string;
  label: string;
  kind: EsmPartnerKind;
};

export type EsmPartnerCandidate = EsmPartner & { score: number };

export type EsmAlignSubject = {
  id: string | null;
  slug: string | null;
  label: string | null;
  kind: EsmPartnerKind;
};

/** Subject A for alignment — lag insights use the feature, not the outcome. */
export function resolveEsmAlignSubject(insight: InsightResponse): EsmAlignSubject | null {
  if (lagFeatureKind(insight)) {
    const feature = lagFeature(insight);
    if (!feature) return null;
    return {
      id: null,
      slug: feature.slug,
      label: feature.name,
      kind: feature.kind,
    };
  }
  if (insight.subject_type === 'tag' || insight.subject_type === 'symptom') {
    const payload = insight.payload ?? {};
    const slug =
      insight.subject_type === 'tag' && typeof payload.tag_slug === 'string'
        ? payload.tag_slug
        : insight.subject_type === 'symptom' && typeof payload.symptom_slug === 'string'
          ? payload.symptom_slug
          : null;
    return {
      id: insight.subject_id,
      slug,
      label: insight.subject_label,
      kind: insight.subject_type,
    };
  }
  return null;
}

function matchesTagRef(
  subject: EsmAlignSubject,
  ref: { tag_id: string; slug: string; name: string }
): boolean {
  if (subject.id && ref.tag_id === subject.id) return true;
  if (subject.slug && ref.slug.toLowerCase() === subject.slug.toLowerCase()) return true;
  if (subject.label && ref.name.toLowerCase() === subject.label.toLowerCase()) return true;
  return false;
}

function matchesSymptomRef(
  subject: EsmAlignSubject,
  ref: { symptom_id: string; slug: string; name: string }
): boolean {
  if (subject.id && ref.symptom_id === subject.id) return true;
  if (subject.slug && ref.slug.toLowerCase() === subject.slug.toLowerCase()) return true;
  if (subject.label && ref.name.toLowerCase() === subject.label.toLowerCase()) return true;
  return false;
}

/** Ranked tag partners for a tag-aligned subject (score = co-occurrence count). */
export function candidatesFromTagCooccurrence(
  subject: EsmAlignSubject,
  pairs: readonly TagCooccurrencePair[]
): EsmPartnerCandidate[] {
  if (subject.kind !== 'tag') return [];
  const byId = new Map<string, EsmPartnerCandidate>();
  for (const pair of pairs) {
    const aMatch = matchesTagRef(subject, pair.tag_a);
    const bMatch = matchesTagRef(subject, pair.tag_b);
    if (aMatch === bMatch) continue;
    const partnerRef = aMatch ? pair.tag_b : pair.tag_a;
    const existing = byId.get(partnerRef.tag_id);
    if (!existing || pair.count > existing.score) {
      byId.set(partnerRef.tag_id, {
        id: partnerRef.tag_id,
        label: partnerRef.name,
        kind: 'tag',
        score: pair.count,
      });
    }
  }
  return [...byId.values()].sort(
    (left, right) => right.score - left.score || left.label.localeCompare(right.label)
  );
}

/**
 * Ranked tag partners for a symptom-aligned subject.
 * Score = |lift − 1| (same preference as backend symptom analytics).
 */
export function candidatesFromSymptomTagCooccurrence(
  subject: EsmAlignSubject,
  cells: readonly SymptomTagCooccurrenceCell[]
): EsmPartnerCandidate[] {
  if (subject.kind !== 'symptom') return [];
  const byId = new Map<string, EsmPartnerCandidate>();
  for (const cell of cells) {
    if (!matchesSymptomRef(subject, cell.symptom)) continue;
    const score = Math.abs(cell.lift - 1);
    const existing = byId.get(cell.tag.tag_id);
    if (!existing || score > existing.score) {
      byId.set(cell.tag.tag_id, {
        id: cell.tag.tag_id,
        label: cell.tag.name,
        kind: 'tag',
        score,
      });
    }
  }
  return [...byId.values()].sort(
    (left, right) => right.score - left.score || left.label.localeCompare(right.label)
  );
}

export function clampPartnerCandidates(
  candidates: readonly EsmPartnerCandidate[],
  limit = ESM_PARTNER_CANDIDATE_LIMIT
): EsmPartnerCandidate[] {
  return candidates.slice(0, Math.max(0, limit));
}

export function pickDefaultPartner(candidates: readonly EsmPartnerCandidate[]): EsmPartner | null {
  const first = candidates[0];
  if (!first) return null;
  return { id: first.id, label: first.label, kind: first.kind };
}

/** Enforce the hard max of one active partner. */
export function clampActivePartners(partners: readonly EsmPartner[]): EsmPartner[] {
  return partners.slice(0, MAX_ESM_PARTNERS);
}

export function presenceDatesFromTagHeatmap(
  heatmap: TagHeatmapResponse | null | undefined,
  tagId: string
): string[] {
  const tag = heatmap?.tags.find((row) => row.tag_id === tagId);
  if (!tag) return [];
  return tag.days.filter((day) => day.count > 0).map((day) => day.date);
}

export function presenceDatesFromSymptomHeatmap(
  heatmap: SymptomHeatmapResponse | null | undefined,
  symptomId: string
): string[] {
  const symptom = heatmap?.symptoms.find((row) => row.symptom_id === symptomId);
  if (!symptom) return [];
  return symptom.days
    .filter((day) => day.count > 0 || (day.max_intensity ?? 0) > 0)
    .map((day) => day.date);
}

export function presenceDatesForPartner(
  partner: EsmPartner | null,
  tagHeatmap: TagHeatmapResponse | null | undefined,
  symptomHeatmap: SymptomHeatmapResponse | null | undefined,
  workContextHeatmap?: WorkContextHeatmapResponse | null
): string[] {
  if (!partner) return [];
  if (partner.kind === 'tag') return presenceDatesFromTagHeatmap(tagHeatmap, partner.id);
  if (partner.kind === 'symptom')
    return presenceDatesFromSymptomHeatmap(symptomHeatmap, partner.id);
  const context = workContextHeatmap?.contexts.find((row) => row.context === partner.id);
  return context?.days.filter((day) => day.count > 0).map((day) => day.date) ?? [];
}

function isoOffset(iso: string, deltaDays: number): string {
  const [y, m, d] = iso.split('-').map(Number);
  const date = new Date(Date.UTC(y, (m ?? 1) - 1, d ?? 1));
  date.setUTCDate(date.getUTCDate() + deltaDays);
  return date.toISOString().slice(0, 10);
}

/** Dates inside an ±radius window around onset where the partner is present. */
export function partnerDatesInWindow(
  onset: string,
  presenceDates: ReadonlySet<string> | readonly string[],
  radius = SMALL_MULTIPLES_RADIUS
): string[] {
  const present = presenceDates instanceof Set ? presenceDates : new Set(presenceDates);
  const hits: string[] = [];
  for (let offset = -radius; offset <= radius; offset += 1) {
    const date = isoOffset(onset, offset);
    if (present.has(date)) hits.push(date);
  }
  return hits;
}

/** Natural-frequency coverage of the partner across the rendered windows (#918). */
export type PartnerWindowCoverage = {
  /** Windows where the partner appears at least once. */
  hits: number;
  /** Rendered windows — the denominator. */
  windows: number;
};

export function countWindowsWithPartner(
  onsets: readonly string[],
  presenceDates: ReadonlySet<string> | readonly string[],
  radius = SMALL_MULTIPLES_RADIUS
): PartnerWindowCoverage {
  const present = presenceDates instanceof Set ? presenceDates : new Set(presenceDates);
  let hits = 0;
  for (const onset of onsets) {
    if (partnerDatesInWindow(onset, present, radius).length > 0) hits += 1;
  }
  return { hits, windows: onsets.length };
}

export function isPartnerPresentOnDate(
  date: string,
  presenceDates: ReadonlySet<string> | readonly string[]
): boolean {
  if (presenceDates instanceof Set) return presenceDates.has(date);
  return (presenceDates as readonly string[]).includes(date);
}
