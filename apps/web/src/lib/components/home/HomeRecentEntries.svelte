<script lang="ts">
  /**
   * HomeRecentEntries — ADR-0014.
   *
   * Renders 7 cards (most recent on top) for the last 7 days. Each
   * card is a clickable link to `/entries/new?date=YYYY-MM-DD`:
   *  - days with an entry render a filled card with mood emoji + tag /
   *    symptom counts and (best-effort) the first two icons
   *  - empty days render a dashed "Kein Eintrag" placeholder card
   *
   * Tag/symptom data is loaded *after* the entries arrive and never
   * blocks the card from rendering. Per-card fetches use
   * `Promise.allSettled` so a single 401/timeout does not break the
   * grid.
   */

  import { _ } from 'svelte-i18n';
  import { onMount } from 'svelte';
  import type { EntryResponse } from '$lib/api/entries';
  import { listTagsForEntry, type TagResponse } from '$lib/api/tags';
  import {
    listSymptomsForEntry,
    type EntrySymptomResponse,
    listVisibleSymptoms,
    type SymptomResponse,
  } from '$lib/api/symptoms';
  import IconRender from '$lib/components/common/IconRender.svelte';
  import { classifyDateLabel } from '$lib/utils/dateLabels';
  import { shiftIsoDate } from '$lib/utils/streak';

  /** Today's local ISO date (YYYY-MM-DD). */
  export let todayIso: string;
  /** Pre-loaded entries from the parent (sorted newest → oldest is fine). */
  export let entries: EntryResponse[] = [];
  /** Surface a loading state to render skeleton cards. */
  export let loading = false;

  // ---------------------------------------------------------------------
  // Derived: 7-day list, anchored on today, oldest → newest is wrong here;
  // the dashboard reads top-down, so we order newest → oldest.
  // ---------------------------------------------------------------------

  interface Slot {
    iso: string;
    entry: EntryResponse | null;
  }

  let slots: Slot[] = [];

  $: {
    const list: Slot[] = [];
    for (let i = 0; i < 7; i += 1) {
      const iso = shiftIsoDate(todayIso, -i);
      const entry = entries.find((e) => e.entry_date === iso && e.slot === 'day') ?? null;
      list.push({ iso, entry });
    }
    slots = list;
  }

  // ---------------------------------------------------------------------
  // Per-entry lazy decorations: tag + symptom previews.
  // ---------------------------------------------------------------------

  type DecoState = {
    tags: TagResponse[];
    symptoms: EntrySymptomResponse[];
  };

  let deco: Record<string, DecoState> = {};
  let symptomLookup: Record<string, SymptomResponse> = {};

  async function loadSymptomLookup() {
    try {
      const visible = await listVisibleSymptoms();
      const map: Record<string, SymptomResponse> = {};
      for (const s of visible) map[s.id] = s;
      symptomLookup = map;
    } catch {
      // Best-effort. Without the lookup we just render counts.
    }
  }

  async function loadDecorationFor(entryId: string) {
    if (deco[entryId]) return;
    const [tagsRes, symRes] = await Promise.allSettled([
      listTagsForEntry(entryId),
      listSymptomsForEntry(entryId),
    ]);
    deco = {
      ...deco,
      [entryId]: {
        tags: tagsRes.status === 'fulfilled' ? tagsRes.value : [],
        symptoms: symRes.status === 'fulfilled' ? symRes.value : [],
      },
    };
  }

  $: {
    for (const s of slots) {
      if (s.entry) void loadDecorationFor(s.entry.id);
    }
  }

  onMount(() => {
    void loadSymptomLookup();
  });

  // ---------------------------------------------------------------------
  // Display helpers
  // ---------------------------------------------------------------------

  const MOOD_EMOJI: Record<number, string> = {
    1: '😢',
    2: '😕',
    3: '😐',
    4: '🙂',
    5: '😄',
  };

  function moodEmoji(score: number): string {
    return MOOD_EMOJI[score] ?? '😐';
  }

  function ariaCardLabel(s: Slot): string {
    if (!s.entry) {
      return $_('home.recent.aria_empty', { values: { date: s.iso } });
    }
    return $_('home.recent.aria_filled', {
      values: { date: s.iso, mood: s.entry.mood_score },
    });
  }
</script>

<section
  class="home-recent"
  data-testid="home-recent-entries"
  aria-label={$_('home.recent.heading')}
>
  <h2 class="home-recent__heading">{$_('home.recent.heading')}</h2>

  <ul class="home-recent__grid">
    {#each slots as slot (slot.iso)}
      {@const label = classifyDateLabel(slot.iso, todayIso)}
      <li class="home-recent__cell">
        <a
          class="home-recent__card"
          class:home-recent__card--empty={!slot.entry}
          class:home-recent__card--skeleton={loading && !slot.entry}
          href={`/entries/new?date=${slot.iso}`}
          aria-label={ariaCardLabel(slot)}
          data-testid={slot.entry
            ? `home-recent-card-${slot.iso}`
            : `home-recent-empty-${slot.iso}`}
          data-has-entry={slot.entry ? 'true' : 'false'}
        >
          <span class="home-recent__date">
            {#if label.kind === 'today'}
              {$_('home.recent.today')}
            {:else if label.kind === 'yesterday'}
              {$_('home.recent.yesterday')}
            {:else}
              {$_(`home.weekday.${label.weekday}`)}
            {/if}
            <span class="home-recent__date-iso">{slot.iso}</span>
          </span>

          {#if slot.entry}
            <span class="home-recent__mood" aria-hidden="true">
              {moodEmoji(slot.entry.mood_score)}
            </span>

            {@const d = deco[slot.entry.id]}
            {#if d}
              <span class="home-recent__chips">
                {#if d.tags.length > 0}
                  <span
                    class="home-recent__chip"
                    title={$_('home.recent.tags_count', {
                      values: { n: d.tags.length },
                    })}
                  >
                    {#each d.tags.slice(0, 2) as t (t.id)}
                      {#if t.icon}
                        <IconRender icon={t.icon} size={14} />
                      {/if}
                    {/each}
                    <span class="home-recent__chip-num">{d.tags.length}</span>
                  </span>
                {/if}
                {#if d.symptoms.length > 0}
                  <span
                    class="home-recent__chip"
                    title={$_('home.recent.symptoms_count', {
                      values: { n: d.symptoms.length },
                    })}
                  >
                    {#each d.symptoms.slice(0, 2) as s (s.symptom_id)}
                      {#if symptomLookup[s.symptom_id]?.icon}
                        <IconRender icon={symptomLookup[s.symptom_id].icon ?? ''} size={14} />
                      {/if}
                    {/each}
                    <span class="home-recent__chip-num">{d.symptoms.length}</span>
                  </span>
                {/if}
              </span>
            {/if}

            {#if slot.entry.note && slot.entry.note.trim().length > 0}
              <span class="home-recent__note">{slot.entry.note.trim()}</span>
            {/if}
          {:else}
            <span class="home-recent__empty-hint">{$_('home.recent.empty_card')}</span>
          {/if}
        </a>
      </li>
    {/each}
  </ul>
</section>

<style>
  .home-recent {
    width: 100%;
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
  }

  .home-recent__heading {
    font-size: var(--text-sm, 0.85rem);
    font-weight: 600;
    opacity: 0.75;
    letter-spacing: 0.02em;
    text-transform: uppercase;
  }

  .home-recent__grid {
    list-style: none;
    margin: 0;
    padding: 0;
    display: flex;
    flex-direction: column;
    gap: 0.4rem;
  }

  .home-recent__cell {
    display: block;
  }

  .home-recent__card {
    display: grid;
    grid-template-columns: 6.5rem auto 1fr;
    align-items: center;
    gap: 0.75rem;
    padding: 0.55rem 0.85rem;
    border-radius: 0.6rem;
    text-decoration: none;
    color: inherit;
    border: 1px solid var(--color-border-chart);
    background: var(--color-surface-chart-bg);
    transition:
      background 120ms ease,
      transform 120ms ease;
  }

  .home-recent__card:hover,
  .home-recent__card:focus-visible {
    background: color-mix(in srgb, var(--color-primary) 8%, transparent);
    transform: translateY(-1px);
  }

  .home-recent__card--empty {
    border-style: dashed;
    background: transparent;
    color: inherit;
    opacity: 0.7;
  }

  .home-recent__card--skeleton {
    pointer-events: none;
  }

  .home-recent__date {
    display: flex;
    flex-direction: column;
    font-weight: 600;
    font-size: var(--text-sm, 0.88rem);
  }

  .home-recent__date-iso {
    font-size: 0.7rem;
    opacity: 0.65;
    font-weight: 400;
  }

  .home-recent__mood {
    font-size: 1.4rem;
    line-height: 1;
  }

  .home-recent__chips {
    display: flex;
    gap: 0.4rem;
    flex-wrap: wrap;
    align-items: center;
  }

  .home-recent__chip {
    display: inline-flex;
    align-items: center;
    gap: 0.2rem;
    font-size: 0.72rem;
    padding: 0.1rem 0.4rem;
    border-radius: 999px;
    background: var(--color-surface-offset);
  }

  .home-recent__chip-num {
    font-weight: 600;
  }

  .home-recent__note {
    grid-column: 1 / -1;
    font-size: 0.72rem;
    opacity: 0.7;
    overflow: hidden;
    display: -webkit-box;
    -webkit-line-clamp: 1;
    -webkit-box-orient: vertical;
    line-clamp: 1;
  }

  .home-recent__empty-hint {
    font-size: 0.75rem;
    opacity: 0.7;
    grid-column: 2 / -1;
  }
</style>
