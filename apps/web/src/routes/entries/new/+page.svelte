<script lang="ts">
  /**
   * /entries/new — daily-entry form (Issue #7).
   *
   * Design constraints (DESIGN_DOCUMENT.md §6 + Issue #7):
   *   - 60-second rule: a default entry should be submittable in ≤ 60 s.
   *     We pre-fill mood/energy/stress to a neutral 3 and pick the date
   *     based on weekday → a typical homeoffice/office/weekend default.
   *   - A11y: each scale has +/- buttons in addition to the slider
   *     (see ScaleSlider).
   *   - Backdating is allowed up to 7 days; the date input is bounded
   *     accordingly.
   *   - On success the user is redirected back to "/" (the timeline /
   *     home page that will land in a sibling issue).
   */

  import { onMount } from 'svelte';
  import { _ } from 'svelte-i18n';
  import { goto } from '$app/navigation';
  import ScaleSlider from '$lib/components/entries/ScaleSlider.svelte';
  import type { WorkContext } from '$lib/api/entries';
  import { submitEntry } from '$lib/stores/entries';
  import { mapApiError, type ApiErrorMap } from '$lib/utils/error';

  // ---------------------------------------------------------------------
  // Form state
  // ---------------------------------------------------------------------

  function isoDate(d: Date): string {
    return d.toISOString().slice(0, 10);
  }

  function defaultWorkContext(d: Date): WorkContext {
    const dow = d.getDay(); // 0 = Sun
    if (dow === 0 || dow === 6) return 'weekend';
    return 'homeoffice';
  }

  const today = new Date();
  const sevenDaysAgo = new Date(today.getTime() - 7 * 24 * 60 * 60 * 1000);

  let entryDate: string = isoDate(today);
  let moodScore = 3;
  let energy = 3;
  let stress = 3;
  let workContext: WorkContext = defaultWorkContext(today);
  let note = '';
  let busy = false;
  let errorKey: string | null = null;

  // Keep the work-context default in sync if the user picks a different
  // day, but only until they manually change it themselves.
  let workContextTouched = false;
  $: if (!workContextTouched && entryDate) {
    const d = new Date(entryDate + 'T00:00:00');
    if (!Number.isNaN(d.getTime())) {
      workContext = defaultWorkContext(d);
    }
  }

  function onWorkContextChange(e: Event) {
    workContextTouched = true;
    workContext = (e.target as HTMLSelectElement).value as WorkContext;
  }

  const ERROR_MAP: ApiErrorMap = {
    401: 'entry.error_unauthenticated',
    409: 'entry.error_conflict',
    422: 'entry.error_too_old',
  };

  const WORK_CONTEXTS: WorkContext[] = [
    'homeoffice',
    'office',
    'vacation',
    'sick',
    'weekend',
    'travel',
  ];

  async function onSubmit() {
    if (busy) return;
    busy = true;
    errorKey = null;
    try {
      await submitEntry({
        entry_date: entryDate,
        slot: 'day',
        mood_score: moodScore,
        energy,
        stress,
        work_context: workContext,
        note: note.trim() ? note.trim() : undefined,
      });
      await goto('/', { replaceState: true });
    } catch (err) {
      errorKey = mapApiError(err, ERROR_MAP) ?? 'entry.error_generic';
    } finally {
      busy = false;
    }
  }

  onMount(() => {
    // Focus the mood slider so a typical "log my day" flow needs zero clicks.
    const el = document.getElementById('entry-mood');
    el?.focus();
  });
</script>

<svelte:head>
  <title>{$_('entry.title')} — {$_('app.name')}</title>
</svelte:head>

<header class="entry-header">
  <h1 class="entry-title">{$_('entry.title')}</h1>
  <p class="entry-subtitle">{$_('entry.subtitle')}</p>
</header>

<form class="entry-form" on:submit|preventDefault={onSubmit} novalidate>
  <label class="entry-field">
    <span class="entry-label">{$_('entry.date_label')}</span>
    <input
      type="date"
      class="input"
      bind:value={entryDate}
      min={isoDate(sevenDaysAgo)}
      max={isoDate(today)}
      required
      disabled={busy}
    />
  </label>

  <ScaleSlider
    id="entry-mood"
    label={$_('entry.mood_label')}
    decrementLabel={$_('entry.mood_decrement')}
    incrementLabel={$_('entry.mood_increment')}
    bind:value={moodScore}
  />

  <ScaleSlider
    id="entry-energy"
    label={$_('entry.energy_label')}
    decrementLabel={$_('entry.energy_decrement')}
    incrementLabel={$_('entry.energy_increment')}
    bind:value={energy}
  />

  <ScaleSlider
    id="entry-stress"
    label={$_('entry.stress_label')}
    decrementLabel={$_('entry.stress_decrement')}
    incrementLabel={$_('entry.stress_increment')}
    bind:value={stress}
  />

  <label class="entry-field">
    <span class="entry-label">{$_('entry.work_context_label')}</span>
    <select class="input" value={workContext} on:change={onWorkContextChange} disabled={busy}>
      {#each WORK_CONTEXTS as wc}
        <option value={wc}>{$_(`entry.work_context.${wc}`)}</option>
      {/each}
    </select>
  </label>

  <label class="entry-field">
    <span class="entry-label">{$_('entry.note_placeholder')}</span>
    <textarea
      class="input"
      rows="4"
      maxlength="4000"
      bind:value={note}
      placeholder={$_('entry.note_placeholder')}
      disabled={busy}
    ></textarea>
  </label>

  {#if errorKey}
    <p class="entry-error" role="alert">{$_(errorKey)}</p>
  {/if}

  <div class="entry-actions">
    <button type="button" class="btn" on:click={() => goto('/')} disabled={busy}>
      {$_('entry.cancel')}
    </button>
    <button type="submit" class="btn variant-filled-primary" disabled={busy}>
      {busy ? $_('entry.save_busy') : $_('entry.save')}
    </button>
  </div>
</form>

<style>
  .entry-header {
    margin-bottom: var(--space-6);
  }

  .entry-title {
    font-size: var(--text-lg);
    font-weight: 600;
    margin-bottom: var(--space-2);
  }

  .entry-subtitle {
    font-size: var(--text-sm);
    opacity: 0.75;
  }

  .entry-form {
    display: flex;
    flex-direction: column;
    gap: var(--space-5);
    max-width: 32rem;
    margin: 0 auto;
  }

  .entry-field {
    display: flex;
    flex-direction: column;
    gap: var(--space-2);
  }

  .entry-label {
    font-size: var(--text-sm);
    font-weight: 500;
  }

  .entry-error {
    font-size: var(--text-sm);
    color: rgb(var(--color-error-500));
    background: rgb(var(--color-error-500) / 0.1);
    border-left: 3px solid rgb(var(--color-error-500));
    padding: var(--space-2) var(--space-3);
    border-radius: 6px;
  }

  .entry-actions {
    display: flex;
    gap: var(--space-3);
    justify-content: flex-end;
    margin-top: var(--space-2);
  }
</style>
