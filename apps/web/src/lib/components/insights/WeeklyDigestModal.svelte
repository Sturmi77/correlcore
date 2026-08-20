<script lang="ts">
  import { onMount } from 'svelte';
  import { _ } from 'svelte-i18n';
  import { goto } from '$app/navigation';
  import { auth } from '$lib/stores/auth';
  import { entrySheetStore } from '$lib/stores/entrySheet';
  import { ApiError } from '$lib/api/client';
  import { fetchLatestInsightDigest, type InsightDigestResponse } from '$lib/api/insights';
  import {
    fetchUserPreferences,
    updateUserPreferences,
    type UserPreferencesResponse,
  } from '$lib/api/preferences';
  import { shouldShowWeeklyDigestModal } from '$lib/utils/weeklyDigestModal';
  import BottomSheet from '$lib/components/common/BottomSheet.svelte';
  import Button from '$lib/components/common/Button.svelte';
  import CorrelationHint from '$lib/components/insights/CorrelationHint.svelte';
  import DigestInsightCards from '$lib/components/insights/DigestInsightCards.svelte';

  // #739: one-time weekly digest modal. On the first authenticated app open
  // after a new stored digest is generated, surface it once. Dismissing it marks
  // the digest seen so it does not reappear until the next week's digest.
  let open = false;
  let digest: InsightDigestResponse | null = null;

  // Yield to the entry/onboarding sheet *reactively*: those sheets can open
  // later in the same session (Home / GlobalEntrySheet), so a one-shot check at
  // decision time is not enough. While a blocking sheet is open we hide the
  // digest modal and re-show it once the sheet closes — never overlaying it.
  $: visible = open && !$entrySheetStore.open;

  const TITLE_ID = 'weekly-digest-modal-title';

  async function maybeShow(): Promise<void> {
    if ($auth.status !== 'authenticated') return;
    let preferences: UserPreferencesResponse;
    try {
      preferences = await fetchUserPreferences();
    } catch {
      return;
    }
    if (!preferences.digest_enabled) return;

    let latest: InsightDigestResponse;
    try {
      latest = await fetchLatestInsightDigest();
    } catch (err) {
      // 404 (not enough insights) / 403 (disabled) / offline → no modal.
      if (!(err instanceof ApiError)) return;
      return;
    }

    // Decide purely on digest freshness; the reactive `visible` gate above
    // defers rendering while a blocking sheet is open (handles either ordering).
    if (shouldShowWeeklyDigestModal({ preferences, digest: latest })) {
      digest = latest;
      open = true;
    }
  }

  async function dismiss(): Promise<void> {
    open = false;
    const generatedAt = digest?.generated_at;
    digest = null;
    if (!generatedAt) return;
    try {
      // Persist so the modal does not reappear until the next digest. Best
      // effort: a failed write just means it may show again on next open.
      await updateUserPreferences({ last_seen_digest_at: generatedAt });
    } catch {
      /* ignore — non-critical UI state */
    }
  }

  function viewFull(): void {
    void dismiss();
    void goto('/insights/digest');
  }

  function onSheetClose(): void {
    // The dialog also emits `close` when we *yield* to a blocking sheet
    // (`visible` → false). That is a temporary hide, not a user dismissal — it
    // must not persist last_seen_digest_at, or a digest the user never saw would
    // be marked seen. During a yield the entry/onboarding sheet is open, so only
    // a genuine close (Esc / backdrop) with no blocking sheet dismisses.
    if ($entrySheetStore.open) return;
    void dismiss();
  }

  onMount(() => {
    void maybeShow();
    // Installed PWA / Capacitor WebViews stay mounted across a background span,
    // so onMount does not re-run when the user returns after the weekly worker
    // ran. Re-check on foreground so a digest generated while backgrounded is
    // still discovered (#739). Skipped while a modal is already open.
    const onVisible = () => {
      if (typeof document !== 'undefined' && document.visibilityState === 'visible' && !open) {
        void maybeShow();
      }
    };
    if (typeof document !== 'undefined') {
      document.addEventListener('visibilitychange', onVisible);
    }
    return () => {
      if (typeof document !== 'undefined') {
        document.removeEventListener('visibilitychange', onVisible);
      }
    };
  });
</script>

{#if open && digest}
  <BottomSheet
    open={visible}
    labelledBy={TITLE_ID}
    testId="weekly-digest-modal"
    closeAriaLabel={$_('insights.digest.modal.close_aria')}
    on:close={onSheetClose}
  >
    <div class="weekly-digest-modal">
      <header class="weekly-digest-modal__head">
        <p class="weekly-digest-modal__eyebrow">{$_('insights.digest.modal.eyebrow')}</p>
        <h2 id={TITLE_ID}>{$_('insights.digest.title')}</h2>
        <p class="weekly-digest-modal__range">
          {$_('insights.digest.range', {
            values: { start: digest.week_start, end: digest.week_end },
          })}
        </p>
      </header>

      <CorrelationHint returnTo="/insights/digest" />
      <DigestInsightCards insights={digest.insights} referenceDate={digest.week_end} />

      <div class="weekly-digest-modal__actions">
        <Button variant="primary" type="button" on:click={viewFull}>
          {$_('insights.digest.modal.view_full')}
        </Button>
        <Button variant="ghost" type="button" on:click={() => void dismiss()}>
          {$_('insights.digest.modal.dismiss')}
        </Button>
      </div>
    </div>
  </BottomSheet>
{/if}

<style>
  .weekly-digest-modal {
    display: grid;
    gap: var(--space-4);
  }

  .weekly-digest-modal__head {
    display: grid;
    gap: var(--space-1);
  }

  .weekly-digest-modal__eyebrow {
    margin: 0;
    font-size: var(--text-xs);
    font-weight: 700;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: var(--color-text-muted);
  }

  .weekly-digest-modal__head h2 {
    margin: 0;
    font-size: var(--text-lg, 1.125rem);
  }

  .weekly-digest-modal__range {
    margin: 0;
    color: var(--color-text-muted);
    font-size: var(--text-sm);
  }

  .weekly-digest-modal__actions {
    display: flex;
    flex-wrap: wrap;
    gap: 0.65rem;
    margin-top: var(--space-2);
  }
</style>
