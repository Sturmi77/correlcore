<script lang="ts">
  import { onMount } from 'svelte';
  import { get } from 'svelte/store';
  import { _ } from 'svelte-i18n';
  import { goto } from '$app/navigation';
  import { auth } from '$lib/stores/auth';
  import { entrySheetStore } from '$lib/stores/entrySheet';
  import {
    weeklyDigestEligibilitySettled,
    weeklyDigestModalOpen,
  } from '$lib/stores/insightAnnouncements';
  import { insightStore, loadInsights } from '$lib/stores/insights';
  import {
    fetchUserPreferences,
    updateUserPreferences,
    type UserPreferencesResponse,
  } from '$lib/api/preferences';
  import type { InsightResponse } from '$lib/api/insights';
  import {
    isNewInsightsPopupAlreadyShownToday,
    markNewInsightsPopupDay,
    shouldShowNewInsightsModal,
  } from '$lib/utils/newInsightsModal';
  import { localIsoDate } from '$lib/utils/home';
  import BottomSheet from '$lib/components/common/BottomSheet.svelte';
  import Button from '$lib/components/common/Button.svelte';
  import CorrelationHint from '$lib/components/insights/CorrelationHint.svelte';
  import InsightCard from '$lib/components/insights/InsightCard.svelte';

  // Once-daily “new insights since last ack” sheet. Yields to the entry sheet
  // and the weekly digest modal (digest has priority). Ack via
  // last_seen_insight_at + per-user local calendar-day gate in localStorage.
  let open = false;
  let candidates: InsightResponse[] = [];
  let ackHighWater: string | null = null;

  $: visible = open && !$entrySheetStore.open && !$weeklyDigestModalOpen;

  const TITLE_ID = 'new-insights-modal-title';

  function currentUserId(): string | null {
    const state = get(auth);
    return state.status === 'authenticated' ? state.user.id : null;
  }

  async function maybeShow(): Promise<void> {
    if ($auth.status !== 'authenticated') return;
    if (open) return;
    if (!get(weeklyDigestEligibilitySettled)) return;
    if (get(weeklyDigestModalOpen)) return;

    const userId = currentUserId();
    if (!userId) return;
    if (isNewInsightsPopupAlreadyShownToday(userId)) return;

    let preferences: UserPreferencesResponse;
    try {
      preferences = await fetchUserPreferences();
    } catch {
      return;
    }

    // Always refresh: a long-lived PWA may hold yesterday's nonempty list and
    // would otherwise skip the fetch and miss a nightly worker run.
    await loadInsights();

    const state = get(insightStore);
    const decision = shouldShowNewInsightsModal({
      preferences,
      insights: state.insights,
      dismissedIds: state.dismissedIds,
      blockingSheetOpen: get(entrySheetStore).open,
      digestModalOpen: get(weeklyDigestModalOpen),
      alreadyShownToday: isNewInsightsPopupAlreadyShownToday(userId),
    });

    if (!decision.show) return;

    candidates = decision.candidates;
    ackHighWater = decision.ackHighWater;
    open = true;
    markNewInsightsPopupDay(userId, localIsoDate(new Date()));
  }

  async function dismiss(): Promise<void> {
    open = false;
    const highWater = ackHighWater;
    candidates = [];
    ackHighWater = null;
    if (!highWater) return;
    try {
      await updateUserPreferences({ last_seen_insight_at: highWater });
    } catch {
      /* best-effort */
    }
  }

  function viewFull(): void {
    void dismiss();
    void goto('/insights');
  }

  function onSheetClose(): void {
    if ($entrySheetStore.open || $weeklyDigestModalOpen) return;
    void dismiss();
  }

  onMount(() => {
    // Wait for WeeklyDigestModal's eligibility check (not a fixed timer) so
    // weekly priority is deterministic even when prefs/digest fetches are slow.
    const unsubSettled = weeklyDigestEligibilitySettled.subscribe((settled) => {
      if (settled && !open) void maybeShow();
    });

    const onVisible = () => {
      if (typeof document !== 'undefined' && document.visibilityState === 'visible' && !open) {
        void maybeShow();
      }
    };
    if (typeof document !== 'undefined') {
      document.addEventListener('visibilitychange', onVisible);
    }

    // After the weekly digest sheet closes, retry once so daily new insights
    // are not permanently skipped when both would have been eligible.
    let sawDigestOpen = false;
    const unsubDigest = weeklyDigestModalOpen.subscribe((digestOpen) => {
      if (digestOpen) {
        sawDigestOpen = true;
        return;
      }
      if (sawDigestOpen && !open) {
        sawDigestOpen = false;
        void maybeShow();
      }
    });

    // Same retry when the entry sheet was open during the initial check
    // (e.g. /?openEntry=1) and later closes.
    let sawEntryOpen = false;
    const unsubEntry = entrySheetStore.subscribe((sheet) => {
      if (sheet.open) {
        sawEntryOpen = true;
        return;
      }
      if (sawEntryOpen && !open) {
        sawEntryOpen = false;
        void maybeShow();
      }
    });

    return () => {
      unsubSettled();
      unsubDigest();
      unsubEntry();
      if (typeof document !== 'undefined') {
        document.removeEventListener('visibilitychange', onVisible);
      }
    };
  });
</script>

{#if open && candidates.length > 0}
  <BottomSheet
    open={visible}
    labelledBy={TITLE_ID}
    testId="new-insights-modal"
    closeAriaLabel={$_('insights.new_modal.close_aria')}
    on:close={onSheetClose}
  >
    <div class="new-insights-modal">
      <header class="new-insights-modal__head">
        <p class="new-insights-modal__eyebrow">{$_('insights.new_modal.eyebrow')}</p>
        <h2 id={TITLE_ID}>{$_('insights.new_modal.title')}</h2>
        <p class="new-insights-modal__subtitle">
          {$_('insights.new_modal.subtitle', { values: { count: candidates.length } })}
        </p>
      </header>

      <CorrelationHint returnTo="/insights" />

      <ul class="new-insights-modal__list">
        {#each candidates as insight (insight.id)}
          <li>
            <InsightCard {insight} showMaturityBadge={false} dismissable={false} />
          </li>
        {/each}
      </ul>

      <div class="new-insights-modal__actions">
        <Button variant="primary" type="button" on:click={viewFull}>
          {$_('insights.new_modal.view_full')}
        </Button>
        <Button variant="ghost" type="button" on:click={() => void dismiss()}>
          {$_('insights.new_modal.dismiss')}
        </Button>
      </div>
    </div>
  </BottomSheet>
{/if}

<style>
  .new-insights-modal {
    display: grid;
    gap: var(--space-4);
  }

  .new-insights-modal__head {
    display: grid;
    gap: var(--space-1);
  }

  .new-insights-modal__eyebrow {
    margin: 0;
    font-size: var(--text-xs);
    font-weight: 700;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: var(--color-text-muted);
  }

  .new-insights-modal__head h2 {
    margin: 0;
    font-size: var(--text-lg, 1.125rem);
  }

  .new-insights-modal__subtitle {
    margin: 0;
    color: var(--color-text-muted);
    font-size: var(--text-sm);
  }

  .new-insights-modal__list {
    list-style: none;
    margin: 0;
    padding: 0;
    display: grid;
    gap: var(--space-3);
  }

  .new-insights-modal__actions {
    display: flex;
    flex-wrap: wrap;
    gap: 0.65rem;
    margin-top: var(--space-2);
  }
</style>
