/**
 * Core metric keys as they appear in insight payloads, mapped to the
 * `trends.metric.*` translation keys. Tag, symptom and context names are user
 * data and are never routed through this table.
 */
const METRIC_I18N_KEY: Readonly<Record<string, string>> = {
  mood: 'mood',
  mood_score: 'mood',
  mood_avg: 'mood',
  energy: 'energy',
  energy_avg: 'energy',
  stress: 'stress',
  stress_avg: 'stress',
  sleep_minutes: 'sleep_minutes',
  sleep_quality: 'sleep_quality',
};

export type Translate = (key: string) => string;

/** Localised name of a core metric key; unknown values are returned unchanged. */
export function localizeMetricKey(value: string, t?: Translate): string {
  const key = METRIC_I18N_KEY[value];
  return key && t ? t(`trends.metric.${key}`) : value;
}
