/**
 * Deterministic lifestyle persona used by Dev Phase fixtures and landing-adjacent
 * mocks. Values are generated from weekday structure + autocorrelated mood, not
 * `idx % n` sawtooths, so charts read like a tracked life rather than a test
 * harness.
 *
 * Primary persona: remote-capable office worker who walks most days, drinks
 * coffee on weekdays, trains a few times a week, and has a drink on some
 * weekends. Sleep is a metric, not a tag.
 */
import type { EntryResponse } from '$lib/api/entries';
import type { TagCooccurrencePair, TagCooccurrenceTagRef } from '$lib/api/insights';
import type { SymptomHeatmapResponse, TagHeatmapResponse } from '$lib/api/stats';
import type { TagCategory } from '$lib/api/tags';
import { shiftIsoDate } from '$lib/utils/streak';

export interface PersonaTagRef {
  tag_id: string;
  slug: string;
  name: string;
  category: TagCategory;
  color: string | null;
}

export interface PersonaSymptomRef {
  symptom_id: string;
  slug: string;
  name: string;
  icon: string;
}

export interface PersonaDay {
  date: string;
  mood: number;
  energy: number;
  stress: number;
  sleepMinutes: number;
  sleepQuality: number;
  workContext: EntryResponse['work_context'];
  tags: PersonaTagRef[];
  symptoms: { ref: PersonaSymptomRef; intensity: number }[];
  note: string | null;
}

export const PERSONA_TAGS = {
  walk: tag('walk', 'Walk', 'health'),
  running: tag('running', 'Running', 'sport'),
  stretching: tag('stretching', 'Stretching', 'sport'),
  strength: tag('strength', 'Strength training', 'sport'),
  meetings: tag('meeting_heavy', 'Meetings', 'work'),
  focus: tag('focus_time', 'Deep work', 'work'),
  commute: tag('commute', 'Commute', 'work'),
  caffeine: tag('caffeine_high', 'Caffeine', 'consumption'),
  alcohol: tag('alcohol', 'Alcohol', 'consumption'),
  family: tag('family', 'Family', 'social'),
  friends: tag('friends', 'Friends', 'social'),
  reading: tag('reading', 'Reading', 'leisure'),
  screen: tag('screen-time', 'Screen time', 'leisure'),
  cooking: tag('cooking', 'Cooking', 'leisure'),
  housework: tag('housework', 'Housework', 'other'),
  nature: tag('nature', 'Nature', 'leisure'),
} as const;

export const PERSONA_SYMPTOMS = {
  fatigue: symptom('fatigue', 'Fatigue', 'battery-low'),
  headache: symptom('headache', 'Headache', 'activity'),
  digestion: symptom('digestion', 'Digestion', 'activity'),
} as const;

function tag(slug: string, name: string, category: TagCategory): PersonaTagRef {
  return { tag_id: `mock-tag-${slug}`, slug, name, category, color: null };
}

function symptom(slug: string, name: string, icon: string): PersonaSymptomRef {
  return { symptom_id: `mock-symptom-${slug}`, slug, name, icon };
}

function hashIso(iso: string, salt: number): number {
  let h = 2166136261 ^ salt;
  for (let i = 0; i < iso.length; i += 1) {
    h ^= iso.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  return h >>> 0;
}

function mulberry32(seed: number): () => number {
  let a = seed || 1;
  return () => {
    a |= 0;
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value));
}

function score(value: number): number {
  return Math.round(clamp(value, 1, 5));
}

function chance(rng: () => number, p: number): boolean {
  return rng() < p;
}

function pickNote(rng: () => number, tags: Set<string>, symptoms: Set<string>): string | null {
  if (rng() > 0.14) return null;
  if (symptoms.has('headache')) return 'Headache from mid-afternoon. Took it slower.';
  if (tags.has('alcohol')) return 'Wine with dinner, bed later than planned.';
  if (tags.has('meeting_heavy') && tags.has('walk')) {
    return 'Back-to-back meetings; walked home anyway.';
  }
  if (tags.has('family')) return 'Easy evening with the kids.';
  if (tags.has('running') || tags.has('strength')) return 'Training left me tired in a useful way.';
  if (tags.has('screen-time')) return 'Scrolled too long after ten.';
  if (tags.has('cooking')) return 'Cooked instead of ordering in.';
  return 'Ordinary day. Logged it anyway.';
}

/** Monday = 0 … Sunday = 6, matching the backend. */
export function pythonWeekday(isoDate: string): number {
  const [year, month, day] = isoDate.split('-').map(Number);
  const jsDay = new Date(year, month - 1, day).getDay();
  return (jsDay + 6) % 7;
}

function collectDates(today: string, entryCount: number): string[] {
  const dates: string[] = [];
  let offset = 0;
  const cap = Math.max(entryCount * 4, 14);
  while (dates.length < entryCount && offset < cap) {
    const date = shiftIsoDate(today, -offset);
    const skipRng = mulberry32(hashIso(date, 0x51ed));
    const skip = offset > 0 && skipRng() < 0.08;
    if (!skip) dates.push(date);
    offset += 1;
  }
  return dates.reverse();
}

const WEEKDAY_MOOD = [3.15, 3.3, 3.35, 3.4, 3.75, 3.95, 3.5];

export function generateOfficeSportDays(today: string, entryCount: number): PersonaDay[] {
  const dates = collectDates(today, Math.max(0, entryCount));
  const days: PersonaDay[] = [];
  let latentMood = 3.4;
  let poorSleep = false;
  let hadAlcohol = false;

  for (const date of dates) {
    const rng = mulberry32(hashIso(date, 0xda7a));
    const weekday = pythonWeekday(date);
    const weekend = weekday >= 5;
    const tags = new Set<string>();
    const symptoms = new Set<string>();

    if (!weekend && chance(rng, 0.88)) tags.add('caffeine_high');
    if (weekend && chance(rng, 0.45)) tags.add('caffeine_high');
    if (!weekend && chance(rng, 0.48)) tags.add('meeting_heavy');
    if (!weekend && chance(rng, 0.32)) tags.add('focus_time');
    if (!weekend && chance(rng, 0.38)) tags.add('commute');
    if (chance(rng, weekend ? 0.62 : 0.52)) tags.add('walk');
    if (chance(rng, weekend ? 0.42 : 0.68)) tags.add('screen-time');
    if (weekend && chance(rng, 0.55)) tags.add('family');
    if (weekend && chance(rng, 0.28)) tags.add('friends');
    if (weekend && chance(rng, 0.4)) tags.add('cooking');
    if (weekend && chance(rng, 0.32)) tags.add('housework');
    if (weekend && chance(rng, 0.22)) tags.add('nature');
    if (chance(rng, 0.22)) tags.add('reading');
    if (!weekend && (weekday === 1 || weekday === 3) && chance(rng, 0.7)) tags.add('stretching');
    if ((weekday === 1 || weekday === 3) && chance(rng, 0.55)) tags.add('strength');
    if (weekday === 5 && chance(rng, 0.5)) tags.add('running');
    if ((weekday === 4 || weekday === 5) && chance(rng, weekday === 5 ? 0.42 : 0.28)) {
      tags.add('alcohol');
    } else if (weekend && chance(rng, 0.12)) {
      tags.add('alcohol');
    }

    const alcohol = tags.has('alcohol');
    const walked = tags.has('walk');
    const trained = tags.has('running') || tags.has('strength');

    if (poorSleep && chance(rng, 0.35)) symptoms.add('headache');
    else if (hadAlcohol && chance(rng, 0.28)) symptoms.add('headache');
    else if (chance(rng, 0.08)) symptoms.add('headache');
    if (alcohol && chance(rng, 0.4)) symptoms.add('digestion');
    if ((poorSleep || trained) && chance(rng, 0.3)) symptoms.add('fatigue');
    else if (weekday === 0 && chance(rng, 0.2)) symptoms.add('fatigue');

    let mood = WEEKDAY_MOOD[weekday] + (rng() - 0.5) * 0.9;
    if (walked) mood += 0.45;
    if (trained) mood += 0.55;
    if (alcohol) mood -= 0.35;
    if (hadAlcohol) mood -= 0.7;
    if (tags.has('meeting_heavy')) mood -= 0.25;
    if (symptoms.has('headache')) mood -= 1.4;
    if (poorSleep) mood -= 0.5;
    if (tags.has('family') && weekend) mood += 0.35;
    latentMood = 0.35 * latentMood + 0.65 * mood;
    const moodScore = score(latentMood);

    let energy = weekend ? 3.6 : 3.2;
    if (walked) energy += 0.35;
    if (trained) energy += 0.2;
    if (hadAlcohol || poorSleep) energy -= 0.7;
    if (symptoms.has('fatigue') || symptoms.has('headache')) energy -= 0.8;
    energy += (rng() - 0.5) * 0.3;

    let stress = weekend ? 2.1 : 3.1;
    if (tags.has('meeting_heavy')) stress += 0.7;
    if (tags.has('focus_time')) stress -= 0.2;
    if (walked) stress -= 0.25;
    if (alcohol) stress -= 0.15;
    stress += (rng() - 0.5) * 0.25;

    let sleepMinutes = weekend ? 470 : 415;
    let sleepQuality = weekend ? 4.1 : 3.4;
    if (alcohol) {
      sleepMinutes -= 55;
      sleepQuality -= 1.2;
    }
    if (tags.has('screen-time')) {
      sleepMinutes -= 20;
      sleepQuality -= 0.4;
    }
    if (trained) sleepQuality += 0.25;
    sleepMinutes += Math.round((rng() - 0.5) * 40);
    sleepQuality += (rng() - 0.5) * 0.3;

    let workContext: EntryResponse['work_context'] = 'office';
    if (weekend) workContext = 'weekend';
    else if (weekday === 0 || weekday === 4)
      workContext = chance(rng, 0.65) ? 'homeoffice' : 'office';
    else workContext = chance(rng, 0.4) ? 'homeoffice' : 'office';

    const tagRefs = [...tags]
      .map((slug) => Object.values(PERSONA_TAGS).find((item) => item.slug === slug))
      .filter((item): item is PersonaTagRef => Boolean(item))
      .slice(0, 5);
    const tagSlugs = new Set(tagRefs.map((item) => item.slug));

    const symptomRefs = [...symptoms]
      .map((slug) => Object.values(PERSONA_SYMPTOMS).find((item) => item.slug === slug))
      .filter((item): item is PersonaSymptomRef => Boolean(item))
      .map((ref) => ({ ref, intensity: 1 + Math.floor(rng() * 2) }));

    days.push({
      date,
      mood: moodScore,
      energy: score(energy),
      stress: score(stress),
      sleepMinutes: clamp(sleepMinutes, 240, 600),
      sleepQuality: score(sleepQuality),
      workContext,
      tags: tagRefs,
      symptoms: symptomRefs,
      note: pickNote(rng, tagSlugs, symptoms),
    });

    poorSleep = sleepQuality < 3;
    hadAlcohol = alcohol;
  }

  return days.reverse();
}

export function daysToEntries(days: PersonaDay[], userId: string): EntryResponse[] {
  return days.map((day, idx) => ({
    id: `mock-entry-${idx}`,
    user_id: userId,
    entry_date: day.date,
    slot: 'day',
    mood_score: day.mood,
    energy: day.energy,
    stress: day.stress,
    cycle_day: null,
    sleep_minutes: Math.round(day.sleepMinutes),
    sleep_quality: day.sleepQuality,
    source: 'direct',
    work_context: day.workContext,
    note: day.note,
    created_at: `${day.date}T09:00:00Z`,
    updated_at: `${day.date}T09:00:00Z`,
  }));
}

export function tagsByEntryId(days: PersonaDay[]): Record<string, string[]> {
  const map: Record<string, string[]> = {};
  days.forEach((day, idx) => {
    map[`mock-entry-${idx}`] = day.tags.map((item) => item.name);
  });
  return map;
}

export function symptomsByEntryId(
  days: PersonaDay[]
): Record<string, { name: string; intensity: number }[]> {
  const map: Record<string, { name: string; intensity: number }[]> = {};
  days.forEach((day, idx) => {
    map[`mock-entry-${idx}`] = day.symptoms.map((item) => ({
      name: item.ref.name,
      intensity: item.intensity,
    }));
  });
  return map;
}

export function tagHeatmapFromDays(days: PersonaDay[], density: number): TagHeatmapResponse {
  const windowDays = days.slice(0, 28);
  const bySlug = new Map<string, { ref: PersonaTagRef; dates: string[] }>();
  for (const day of windowDays) {
    for (const tagRef of day.tags) {
      const bucket = bySlug.get(tagRef.slug) ?? { ref: tagRef, dates: [] };
      bucket.dates.push(day.date);
      bySlug.set(tagRef.slug, bucket);
    }
  }
  const ranked = [...bySlug.values()].sort((a, b) => b.dates.length - a.dates.length);
  const keep = density === 0 ? [] : ranked.slice(0, Math.max(2, density));
  return {
    start_date: windowDays.at(-1)?.date ?? days[0]?.date ?? '',
    end_date: days[0]?.date ?? '',
    tags: keep.map((item) => ({
      ...item.ref,
      days: item.dates.map((date) => ({ date, count: 1 })),
    })),
  };
}

export function symptomHeatmapFromDays(
  days: PersonaDay[],
  density: number
): SymptomHeatmapResponse {
  const windowDays = days.slice(0, 28);
  const bySlug = new Map<
    string,
    { ref: PersonaSymptomRef; days: { date: string; count: number; max_intensity: number }[] }
  >();
  for (const day of windowDays) {
    for (const item of day.symptoms) {
      const bucket = bySlug.get(item.ref.slug) ?? { ref: item.ref, days: [] };
      bucket.days.push({ date: day.date, count: 1, max_intensity: item.intensity });
      bySlug.set(item.ref.slug, bucket);
    }
  }
  const ranked = [...bySlug.values()].sort((a, b) => b.days.length - a.days.length);
  return {
    start_date: windowDays.at(-1)?.date ?? days[0]?.date ?? '',
    end_date: days[0]?.date ?? '',
    symptoms:
      density <= 1
        ? []
        : ranked.slice(0, Math.max(2, Math.min(density, 4))).map((item) => ({
            ...item.ref,
            days: item.days,
          })),
  };
}

function pairKey(a: string, b: string): string {
  return a < b ? `${a}:${b}` : `${b}:${a}`;
}

export function tagPairsFromDays(days: PersonaDay[], startOffset: number): TagCooccurrencePair[] {
  const window = days.filter((day) => day.date >= shiftIsoDate(days[0]?.date ?? '', startOffset));
  const tagBySlug = new Map<string, PersonaTagRef>();
  const tagCount = new Map<string, number>();
  const pairCount = new Map<string, number>();

  for (const day of window) {
    const slugs = [...new Set(day.tags.map((item) => item.slug))];
    for (const tagRef of day.tags) tagBySlug.set(tagRef.slug, tagRef);
    for (const slug of slugs) tagCount.set(slug, (tagCount.get(slug) ?? 0) + 1);
    for (let i = 0; i < slugs.length; i += 1) {
      for (let j = i + 1; j < slugs.length; j += 1) {
        const key = pairKey(slugs[i], slugs[j]);
        pairCount.set(key, (pairCount.get(key) ?? 0) + 1);
      }
    }
  }

  const asRef = (slug: string): TagCooccurrenceTagRef => {
    const ref = tagBySlug.get(slug)!;
    return {
      tag_id: ref.tag_id,
      slug: ref.slug,
      name: ref.name,
      category: ref.category,
      color: ref.color,
    };
  };

  return [...pairCount.entries()]
    .filter(([, count]) => count >= 2)
    .sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]))
    .slice(0, 8)
    .map(([key, count]) => {
      const [slugA, slugB] = key.split(':');
      const countA = tagCount.get(slugA) ?? count;
      const countB = tagCount.get(slugB) ?? count;
      return {
        tag_a: asRef(slugA),
        tag_b: asRef(slugB),
        count,
        pct_of_a: Number(((count / countA) * 100).toFixed(1)),
        pct_of_b: Number(((count / countB) * 100).toFixed(1)),
      };
    });
}
