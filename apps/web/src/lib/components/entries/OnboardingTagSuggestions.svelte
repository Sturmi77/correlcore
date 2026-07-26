<script lang="ts">
  import { createEventDispatcher } from 'svelte';
  import { _ } from 'svelte-i18n';
  import type { TagSuggestion, TagSuggestionGroup } from '$lib/api/onboarding';
  import ConceptExplainer from '$lib/components/onboarding/ConceptExplainer.svelte';

  export let groups: TagSuggestionGroup[] = [];
  export let loading = false;
  export let selectedSlugs: ReadonlySet<string> = new Set();
  export let disabled = false;

  const dispatch = createEventDispatcher<{ toggle: TagSuggestion }>();
</script>

<section class="onboarding-tags" aria-labelledby="entry-onboarding-tags-title">
  <p class="onboarding-tags__intro" data-testid="onboarding-intro">
    {$_('onboarding.guided.intro')}
  </p>
  <h2 id="entry-onboarding-tags-title" class="onboarding-tags__title">
    {$_('entry.onboarding_tags.title')}
  </h2>
  <ConceptExplainer />
  <p class="onboarding-tags__habit-hint" data-testid="onboarding-habit-hint">
    {$_('onboarding.guided.habit_hint')}
  </p>

  {#if loading}
    <p class="onboarding-tags__loading">{$_('tag.loading')}</p>
  {:else}
    <div class="onboarding-tags__groups">
      {#each groups as group}
        <div class="onboarding-tags__group">
          <h3>{$_(`tag.category.${group.category}`)}</h3>
          <div class="onboarding-tags__chips" role="group">
            {#each group.suggestions as tag}
              <button
                type="button"
                class:active={selectedSlugs.has(tag.slug)}
                aria-pressed={selectedSlugs.has(tag.slug)}
                {disabled}
                data-testid="onboarding-tag-suggestion"
                on:click={() => dispatch('toggle', tag)}
              >
                {tag.name}
              </button>
            {/each}
          </div>
        </div>
      {/each}
    </div>
  {/if}
</section>

<style>
  .onboarding-tags {
    display: flex;
    flex-direction: column;
    gap: var(--space-3);
  }

  .onboarding-tags__intro {
    margin: 0;
    font-size: var(--text-sm);
    line-height: 1.5;
    color: var(--color-text);
  }

  .onboarding-tags__title {
    margin: 0;
    font-size: var(--text-sm);
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.02em;
  }

  .onboarding-tags__habit-hint {
    margin: 0;
    font-size: var(--text-sm);
    line-height: 1.5;
    color: var(--color-text-muted);
    padding: var(--space-3);
    border-radius: var(--radius-sm);
    background: color-mix(in srgb, var(--color-primary) 8%, transparent);
    border: 1px solid color-mix(in srgb, var(--color-primary) 18%, transparent);
  }

  .onboarding-tags__loading {
    margin: 0;
    font-size: var(--text-sm);
    color: var(--color-text-muted);
  }

  .onboarding-tags__groups {
    display: flex;
    flex-direction: column;
    gap: var(--space-4);
  }

  .onboarding-tags__group h3 {
    margin: 0 0 var(--space-2);
    font-size: var(--text-sm);
    font-weight: 600;
  }

  .onboarding-tags__chips {
    display: flex;
    flex-wrap: wrap;
    gap: var(--space-2);
  }

  .onboarding-tags__chips button {
    min-height: 44px;
    border: 1px solid var(--color-border);
    border-radius: var(--radius-sm);
    background: var(--color-surface-2);
    color: var(--color-text);
    padding: var(--space-2) var(--space-3);
    cursor: pointer;
  }

  .onboarding-tags__chips button.active {
    border-color: var(--color-primary);
    background: var(--color-primary-soft);
    color: var(--color-primary);
    font-weight: 650;
  }

  .onboarding-tags__chips button:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }
</style>
