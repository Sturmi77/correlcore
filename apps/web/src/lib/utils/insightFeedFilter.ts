import type { InsightResponse } from '$lib/api/insights';
import { isCalendarContextInsight } from '$lib/utils/insightConfounder';
import { rankInsights } from '$lib/utils/insightRanking';

export type InsightFeedFilterTab = 'all' | 'mood' | 'symptoms' | 'context';

type TabBarOptionLike = {
  id: string;
  label: string;
  disabled?: boolean;
  testId?: string;
};

export const INSIGHT_FEED_FILTER_TABS: { id: InsightFeedFilterTab; label: string }[] = [
  { id: 'all', label: 'insights.feed.tab_all' },
  { id: 'mood', label: 'insights.feed.tab_mood' },
  { id: 'symptoms', label: 'insights.feed.tab_symptoms' },
  { id: 'context', label: 'insights.feed.tab_context' },
];

const METRIC_MAP: Record<InsightFeedFilterTab, string[]> = {
  all: [],
  mood: ['mood'],
  symptoms: ['symptom', 'symptoms'],
  context: [],
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
): TabBarOptionLike[] {
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
    if (activeTab === 'context') return isCalendarContextInsight(insight);
    return insightMatches(insight, METRIC_MAP[activeTab]);
  });
}

export function rankedInsightsForTab(
  insights: InsightResponse[],
  activeTab: InsightFeedFilterTab
): InsightResponse[] {
  return rankInsights(filterInsightsByTab(insights, activeTab));
}
