<script lang="ts">
  import { createEventDispatcher } from 'svelte';
  import { _ } from 'svelte-i18n';
  import type { EntryNoteMarkerResponse } from '$lib/api/noteMarkers';
  import { PREDEFINED_NOTE_MARKERS } from '$lib/api/noteMarkers';

  export let markers: EntryNoteMarkerResponse[] = [];
  export let readonly = false;
  export let suggestions: string[] = [];

  const dispatch = createEventDispatcher<{
    toggle: { marker: string; selected: boolean };
    addCustom: { marker: string };
  }>();

  let customMarker = '';

  $: selected = new Set(markers.map((marker) => marker.marker));
  $: customSuggestions = (() => {
    const fromSuggestions = suggestions.filter(
      (marker) => !PREDEFINED_NOTE_MARKERS.includes(marker as never)
    );
    const fromSelected = markers
      .map((marker) => marker.marker)
      .filter((marker) => !PREDEFINED_NOTE_MARKERS.includes(marker as never));
    return [...new Set([...fromSuggestions, ...fromSelected])];
  })();

  function toggle(marker: string): void {
    if (readonly) return;
    dispatch('toggle', { marker, selected: !selected.has(marker) });
  }

  function submitCustom(): void {
    const value = customMarker.trim();
    if (!value || readonly) return;
    dispatch('addCustom', { marker: value });
    customMarker = '';
  }
</script>

<div class="note-markers" data-testid="note-marker-chips">
  <div class="note-markers__row" role="group" aria-label={$_('entry.note_markers.aria')}>
    {#each PREDEFINED_NOTE_MARKERS as marker (marker)}
      <button
        type="button"
        class="note-markers__chip"
        class:note-markers__chip--active={selected.has(marker)}
        aria-pressed={selected.has(marker)}
        disabled={readonly}
        data-testid={`note-marker-${marker}`}
        on:click={() => toggle(marker)}
      >
        {$_(`entry.note_markers.${marker}`)}
      </button>
    {/each}
    {#each customSuggestions as marker (marker)}
      <button
        type="button"
        class="note-markers__chip note-markers__chip--custom"
        class:note-markers__chip--active={selected.has(marker)}
        aria-pressed={selected.has(marker)}
        disabled={readonly}
        on:click={() => toggle(marker)}
      >
        {marker}
      </button>
    {/each}
  </div>

  {#if !readonly}
    <div class="note-markers__custom">
      <input
        type="text"
        maxlength="32"
        bind:value={customMarker}
        placeholder={$_('entry.note_markers.custom_placeholder')}
        data-testid="note-marker-custom-input"
        on:keydown={(event) => event.key === 'Enter' && (event.preventDefault(), submitCustom())}
      />
      <button type="button" class="note-markers__add" on:click={submitCustom}>
        {$_('entry.note_markers.add_custom')}
      </button>
    </div>
  {/if}
</div>

<style>
  .note-markers {
    display: flex;
    flex-direction: column;
    gap: var(--space-2);
  }

  .note-markers__row {
    display: flex;
    flex-wrap: wrap;
    gap: var(--space-1);
  }

  .note-markers__chip {
    min-height: var(--tap-target);
    padding: 0 var(--space-2);
    border-radius: var(--radius-full);
    border: 1px solid var(--color-border);
    background: var(--color-surface);
    color: var(--color-text-muted);
    font-size: var(--text-xs);
    font-weight: 600;
    cursor: pointer;
  }

  .note-markers__chip--active {
    border-color: color-mix(in srgb, var(--color-primary) 35%, var(--color-border));
    background: color-mix(in srgb, var(--color-primary) 12%, var(--color-surface));
    color: var(--color-primary);
  }

  .note-markers__custom {
    display: flex;
    gap: var(--space-2);
    align-items: center;
  }

  .note-markers__custom input {
    flex: 1;
    min-height: var(--tap-target);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-sm);
    padding: 0 var(--space-2);
    background: var(--color-surface);
    color: inherit;
    font-size: var(--text-sm);
  }

  .note-markers__add {
    min-height: var(--tap-target);
    padding: 0 var(--space-3);
    border-radius: var(--radius-sm);
    border: 1px solid var(--color-border);
    background: var(--color-surface-offset);
    color: var(--color-primary);
    font-size: var(--text-xs);
    font-weight: 700;
    cursor: pointer;
  }
</style>
