<script lang="ts">
  import { onMount } from 'svelte';
  import { _ } from 'svelte-i18n';
  import { page } from '$app/stores';
  import { auth } from '$lib/stores/auth';
  import ThemeToggle from '$lib/components/common/ThemeToggle.svelte';
  import ScreenHeader from '$lib/components/common/ScreenHeader.svelte';
  import IconRender from '$lib/components/common/IconRender.svelte';
  import { listEntries, type EntryResponse } from '$lib/api/entries';
  import NoteMarkerChips from '$lib/components/entries/NoteMarkerChips.svelte';
  import NoteSignalsList from '$lib/components/entries/NoteSignalsList.svelte';
  import { listTagsForEntry, type TagResponse } from '$lib/api/tags';
  import {
    listSymptomsForEntry,
    listVisibleSymptoms,
    type EntrySymptomResponse,
    type SymptomResponse,
  } from '$lib/api/symptoms';
  import { ICON_SIZE_SM } from '$lib/constants/iconSizes';
  import { isEntryDateEditable } from '$lib/utils/entryForm';

  type EntryDecorations = {
    tags: TagResponse[];
    symptoms: EntrySymptomResponse[];
  };

  let loading = true;
  let error = '';
  let entries: EntryResponse[] = [];
  let decorations: Record<string, EntryDecorations> = {};
  let symptomLookup: Record<string, SymptomResponse> = {};
  let notesOnly = false;

  $: date = $page.params.date ?? '';
  $: selectedTagId = $page.url.searchParams.get('tag_id');
  $: validDate = /^\d{4}-\d{2}-\d{2}$/.test(date);
  $: editableDate = validDate && isEntryDateEditable(new Date(), date);
  $: visibleEntries = (selectedTagId
    ? entries.filter((entry) => decorations[entry.id]?.tags.some((tag) => tag.id === selectedTagId))
    : entries
  ).filter((entry) => !notesOnly || Boolean(entry.note?.trim() || entry.note_summary_short?.trim()));

  const MOOD_LABELS: Record<number, string> = {
    1: 'entry.mood_terrible',
    2: 'entry.mood_bad',
    3: 'entry.mood_okay',
    4: 'entry.mood_good',
    5: 'entry.mood_great',
  };

  async function load(): Promise<void> {
    if ($auth.status !== 'authenticated') {
      loading = false;
      return;
    }
    if (!validDate) {
      error = $_('day_entries.invalid_date');
      loading = false;
      return;
    }

    loading = true;
    error = '';
    try {
      const [dayEntries, symptoms] = await Promise.all([
        listEntries({ start_date: date, end_date: date, limit: 365 }),
        listVisibleSymptoms(),
      ]);
      entries = dayEntries.filter((entry) => entry.entry_date === date);
      symptomLookup = Object.fromEntries(symptoms.map((symptom) => [symptom.id, symptom]));

      const pairs = await Promise.all(
        entries.map(async (entry) => {
          const [tagsRes, symptomsRes] = await Promise.allSettled([
            listTagsForEntry(entry.id),
            listSymptomsForEntry(entry.id),
          ]);
          return [
            entry.id,
            {
              tags: tagsRes.status === 'fulfilled' ? tagsRes.value : [],
              symptoms: symptomsRes.status === 'fulfilled' ? symptomsRes.value : [],
            },
          ] as const;
        })
      );
      decorations = Object.fromEntries(pairs);
    } catch (err) {
      error = err instanceof Error ? err.message : $_('error.generic');
      entries = [];
      decorations = {};
    } finally {
      loading = false;
    }
  }

  function moodLabel(score: number): string {
    return $_(MOOD_LABELS[score] ?? 'entry.mood_okay');
  }

  onMount(() => {
    void load();
  });
</script>

<svelte:head>
  <title>{$_('day_entries.title')} - {$_('app.name')}</title>
</svelte:head>

<main class="day-entries">
  <ScreenHeader title={$_('day_entries.title')} subtitle={date} visuallyHidden />

  <header class="day-entries__top">
    <a class="btn btn-sm variant-ghost-surface" href="/trends">{$_('nav.trends')}</a>
    <ThemeToggle testId="day-entries-theme-toggle" />
  </header>

  <section class="day-entries__intro">
    <div>
      <h2 class="day-entries__heading">{$_('day_entries.title')}</h2>
      <p>{date}</p>
    </div>
    {#if editableDate}
      <a class="btn btn-sm btn--secondary" href={`/entries/new?date=${date}`}>
        {$_('day_entries.add_or_edit')}
      </a>
    {/if}
  </section>

  <label class="day-entries__filter">
    <input type="checkbox" bind:checked={notesOnly} data-testid="day-entries-notes-only" />
    <span>{$_('day_entries.filter_notes_only')}</span>
  </label>

  {#if validDate && !editableDate}
    <p class="day-entries__read-only" role="status" data-testid="day-entry-read-only">
      {$_('day_entries.read_only')}
    </p>
  {/if}

  {#if $auth.status !== 'authenticated'}
    <section class="day-entries__panel">
      <p>{$_('trends.auth_required')}</p>
      <a class="btn btn-sm btn--primary" href="/auth/login">{$_('auth.login.submit')}</a>
    </section>
  {:else if loading}
    <section class="day-entries__panel" aria-busy="true">
      <p>{$_('day_entries.loading')}</p>
    </section>
  {:else if error}
    <p class="day-entries__error" role="alert">{error}</p>
  {:else if visibleEntries.length === 0}
    <section class="day-entries__panel day-entries__empty">
      <p>
        {selectedTagId ? $_('day_entries.empty_for_tag') : $_('day_entries.empty')}
      </p>
      {#if editableDate}
        <a class="btn btn-sm btn--primary" href={`/entries/new?date=${date}`}>
          {$_('day_entries.create')}
        </a>
      {/if}
    </section>
  {:else}
    <section class="day-entries__list" aria-label={$_('day_entries.list_aria')}>
      {#each visibleEntries as entry (entry.id)}
        {@const deco = decorations[entry.id]}
        <article class="day-entries__card">
          <div class="day-entries__card-head">
            <div>
              <h2>{moodLabel(entry.mood_score)}</h2>
              <p>
                {$_('day_entries.score_line', {
                  values: {
                    mood: entry.mood_score,
                    energy: entry.energy,
                    stress: entry.stress,
                  },
                })}
              </p>
            </div>
            {#if editableDate}
              <a
                class="btn btn-sm variant-ghost-surface"
                href={`/entries/new?date=${entry.entry_date}`}
              >
                {$_('day_entries.edit')}
              </a>
            {/if}
          </div>

          {#if entry.note}
            <p class="day-entries__note">{entry.note}</p>
          {/if}
          {#if entry.note_markers && entry.note_markers.length > 0}
            <NoteMarkerChips markers={entry.note_markers} readonly />
          {/if}
          {#if entry.note_signals && entry.note_signals.length > 0}
            <NoteSignalsList signals={entry.note_signals} />
          {/if}

          {#if deco?.tags.length}
            <div class="day-entries__chips" aria-label={$_('tag.picker_label')}>
              {#each deco.tags as tag (tag.id)}
                <span class:active={tag.id === selectedTagId}>
                  {#if tag.icon}<IconRender icon={tag.icon} size={ICON_SIZE_SM} />{/if}
                  {tag.name}
                </span>
              {/each}
            </div>
          {/if}

          {#if deco?.symptoms.length}
            <div class="day-entries__chips" aria-label={$_('symptom.picker_label')}>
              {#each deco.symptoms as symptom (symptom.symptom_id)}
                {@const visibleSymptom = symptomLookup[symptom.symptom_id]}
                <span>
                  {#if visibleSymptom?.icon}<IconRender
                      icon={visibleSymptom.icon}
                      size={ICON_SIZE_SM}
                    />{/if}
                  {visibleSymptom?.name ?? $_('symptom.picker_label')}
                  <strong>{symptom.intensity}</strong>
                </span>
              {/each}
            </div>
          {/if}
        </article>
      {/each}
    </section>
  {/if}
</main>

<style>
  .day-entries {
    width: min(100%, 48rem);
    margin: 0 auto;
    padding: 1.25rem;
    display: flex;
    flex-direction: column;
    gap: 1rem;
  }

  .day-entries__top,
  .day-entries__intro,
  .day-entries__card-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 1rem;
  }

  .day-entries__intro h2,
  .day-entries__card h2 {
    margin: 0;
    font-size: var(--text-xl, 1.25rem);
    font-weight: 700;
  }

  .day-entries__intro p,
  .day-entries__card p {
    margin: 0.25rem 0 0;
    opacity: 0.72;
  }

  .day-entries__panel,
  .day-entries__card {
    padding: 1rem;
    border-radius: var(--radius-md);
    background: var(--color-surface-chart-bg);
    border: 1px solid var(--color-border-chart);
  }

  .day-entries__list {
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
  }

  .day-entries__card {
    display: flex;
    flex-direction: column;
    gap: 0.8rem;
  }

  .day-entries__note {
    white-space: pre-wrap;
    line-height: 1.45;
  }

  .day-entries__chips {
    display: flex;
    flex-wrap: wrap;
    gap: 0.45rem;
  }

  .day-entries__chips span {
    display: inline-flex;
    align-items: center;
    gap: 0.25rem;
    padding: 0.22rem 0.5rem;
    border-radius: var(--radius-full);
    background: var(--color-surface-offset);
    font-size: var(--text-xs);
  }

  .day-entries__chips span.active {
    background: var(--color-primary);
    color: var(--color-text-inverse);
  }

  .day-entries__chips strong {
    font-weight: 700;
  }

  .day-entries__error {
    margin: 0;
    color: var(--color-error);
  }

  .day-entries__read-only {
    margin: 0;
    padding: 0.75rem 1rem;
    border-left: 3px solid var(--color-warning);
    border-radius: var(--radius-sm);
    background: color-mix(in srgb, var(--color-warning) 10%, transparent);
    color: var(--color-text);
  }

  .day-entries__empty {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 1rem;
  }

  @media (max-width: 480px) {
    .day-entries {
      padding: 1rem;
    }

    .day-entries__intro,
    .day-entries__card-head,
    .day-entries__empty {
      align-items: stretch;
      flex-direction: column;
    }
  }
</style>
