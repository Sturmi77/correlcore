import type { InsightResponse } from '$lib/api/insights';
import { rankInsights } from '$lib/utils/insightRanking';
import type { TabBarOption } from '$lib/components/common/TabBar.svelte';

export type InsightFeedFilterTab = 'all' | 'mood' | 'symptoms' | 'sleep';

export const INSIGHT_FEED_FILTER_TABS: { id: InsightFeedFilterTab; label: string }[] = [
  { id: 'all', label: 'insights.feed.tab_all' },
  { id: 'mood', label: 'insights.feed.tab_mood' },
  { id: 'symptoms', label: 'insights.feed.tab_symptoms' },
  { id: 'sleep', label: 'insights.feed.tab_sleep' },
];

const METRIC_MAP: Record<InsightFeedFilterTab, string[]> = {
  all: [],
  mood: ['mood'],
  symptoms: ['symptom', 'symptoms'],
  sleep: ['sleep'],
};

function insightMatches(i: InsightResponse, keywords: string[]): boolean {
  const tokens = [
    i.metric,
    i.insight_type,
    i.subject_type,
    i.subject_label,
    typeof i.payload?.kind === 'string' ? i.payload.kind : '',
    typeof i.flags?.kind === 'string' ? i.flags.kind : '',
  ]
    .filter(Boolean)
    .map((token) => String(token).toLowerCase());
  return keywords.some((keyword) => tokens.some((token) => token.includes(keyword)));
}

export function getInsightFeedFilterTabs(
  translate: (key: string) => string,
  testIdPrefix = 'insights-filter-tab'
): TabBarOption[] {
  return INSIGHT_FEED_FILTER_TABS.map((tab) => ({
    id: tab.id,
    label: translate(tab.label),
    testId: `${testIdPrefix}-${tab.id}`,
  }));
}

export function filterInsightsByTab(
  insights: InsightResponse[],
  activeTab: InsightFeedFilterTab
): InsightResponse[] {
  return insights.filter((insight) => {
    if (activeTab === 'all') return true;
    return insightMatches(insight, METRIC_MAP[activeTab]);
  });
}

export function rankedInsightsForTab(
  insights: InsightResponse[],
  activeTab: InsightFeedFilterTab
): InsightResponse[] {
  return rankInsights(filterInsightsByTab(insights, activeTab));
}
