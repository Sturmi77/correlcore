<script lang="ts">
  import { onMount } from 'svelte';
  import { get } from 'svelte/store';
  import { goto } from '$app/navigation';
  import { page } from '$app/stores';
  import { _ } from 'svelte-i18n';
  import Button from '$lib/components/common/Button.svelte';
  import InlineAlert from '$lib/components/common/InlineAlert.svelte';
  import Panel from '$lib/components/common/Panel.svelte';
  import ScreenHeader from '$lib/components/common/ScreenHeader.svelte';
  import ConceptExplainer from '$lib/components/onboarding/ConceptExplainer.svelte';
  import MaturityExpectationContent from '$lib/components/onboarding/MaturityExpectationContent.svelte';
  import CycleFunctionExplainer from '$lib/components/onboarding/CycleFunctionExplainer.svelte';
  import {
    completeOnboarding,
    fetchTagSuggestions,
    type OnboardingTagInput,
    type TagSuggestion,
    type TagSuggestionGroup,
  } from '$lib/api/onboarding';
  import { fetchUserPreferences, updateUserPreferences } from '$lib/api/preferences';
  import { TAG_CATEGORIES, type TagCategory, type HabitType } from '$lib/api/tags';
  import { OPEN_ENTRY_HOME_PATH } from '$lib/navigation/openEntry';
  import { shouldSkipOnboardingSummary } from '$lib/utils/onboardingEntry';
  import { writeOnboardingSuggestionStash } from '$lib/utils/onboardingSuggestionStash';
  import { localizedCatalogName } from '$lib/utils/localizedCatalogName';
  import { currentUser } from '$lib/stores/auth';
  import { connectivity } from '$lib/stores/connectivity';

  type StepId = 'maturity' | 'concepts' | 'tags' | 'goals' | 'summary' | 'cycle';

  type HabitChoice = { habit_type: HabitType; target_frequency: number };

  let stepIndex = 0;
  let groups: TagSuggestionGroup[] = [];
  let selected = new Map<string, TagSuggestion>();
  // Optional habit facet per selected tag (#564). Absent slug = plain tag.
  let habitBySlug = new Map<string, HabitChoice>();
  let customName = '';
  let customCategory: TagCategory = 'other';
  let cycleEnabled = true;
  let checking = true;
  let loading = true;
  let busy = false;
  let error = '';
  let customError = '';
  const customCategories = TAG_CATEGORIES;

  $: selectedTags = [...selected.values()];
  // Custom picks are not part of any suggestion group, so render them as their
  // own removable chip row — otherwise a wrong custom tag cannot be undone
  // without reloading the wizard.
  $: suggestionSlugs = new Set(groups.flatMap((g) => g.suggestions.map((s) => s.slug)));
  $: customSelected = selectedTags.filter((tag) => !suggestionSlugs.has(tag.slug));

  function tagLabel(tag: TagSuggestion): string {
    return localizedCatalogName(tag.slug, suggestionSlugs.has(tag.slug), tag.name, $_);
  }
  $: showSummaryStep = !shouldSkipOnboardingSummary(selectedTags.length);
  // The optional goals step only appears once at least one tag is picked.
  $: showGoalsStep = selectedTags.length > 0;
  // Cycle is always the last screen; the summary only appears with > 3 tags.
  $: steps = [
    'maturity',
    'concepts',
    'tags',
    ...(showGoalsStep ? (['goals'] as StepId[]) : []),
    ...(showSummaryStep ? (['summary'] as StepId[]) : []),
    'cycle',
  ] as StepId[];
  // Clamp so a shrinking `steps` (user reduces tags below the summary threshold
  // while on a later index) can never point past the end.
  $: if (stepIndex > steps.length - 1) stepIndex = steps.length - 1;
  $: currentStep = steps[stepIndex] ?? 'maturity';
  $: isLastStep = stepIndex === steps.length - 1;
  $: progressLabel = `${stepIndex + 1}/${steps.length}`;

  // Settings → Developer opens `/onboarding?preview=1` in an iframe to preview
  // the wizard; keep that bypass working even for already-onboarded users.
  const previewMode = get(page).url.searchParams.get('preview') === '1';

  onMount(async () => {
    try {
      const preferences = await fetchUserPreferences();
      if (!previewMode && preferences.onboarding_retro_completed) {
        await goto('/');
        return;
      }
    } catch {
      // No preferences yet / offline — treat as not-onboarded and continue.
    } finally {
      checking = false;
    }
    try {
      groups = (await fetchTagSuggestions()).groups;
    } catch (err) {
      error = err instanceof Error ? err.message : $_('error.generic');
    } finally {
      loading = false;
    }
  });

  function toggleSuggestion(tag: TagSuggestion) {
    selected = new Map(selected);
    if (selected.has(tag.slug)) {
      selected.delete(tag.slug);
      // Drop any habit choice for a tag that is no longer picked.
      if (habitBySlug.has(tag.slug)) {
        habitBySlug = new Map(habitBySlug);
        habitBySlug.delete(tag.slug);
      }
    } else {
      selected.set(tag.slug, tag);
    }
  }

  const HABIT_TYPES: HabitType[] = ['none', 'build', 'reduce'];

  function habitTypeFor(slug: string): HabitType {
    return habitBySlug.get(slug)?.habit_type ?? 'none';
  }

  function habitFreqFor(slug: string): number {
    return habitBySlug.get(slug)?.target_frequency ?? 3;
  }

  function setHabitType(slug: string, habit_type: HabitType) {
    habitBySlug = new Map(habitBySlug);
    if (habit_type === 'none') {
      habitBySlug.delete(slug);
    } else {
      habitBySlug.set(slug, {
        habit_type,
        target_frequency: habitBySlug.get(slug)?.target_frequency ?? 3,
      });
    }
  }

  function setHabitFreq(slug: string, target_frequency: number) {
    const current = habitBySlug.get(slug);
    if (!current) return;
    habitBySlug = new Map(habitBySlug).set(slug, { ...current, target_frequency });
  }

  function addCustomTag() {
    const name = customName.trim();
    if (!name) return;
    const slug = name
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, '-')
      .replace(/^-+|-+$/g, '')
      .slice(0, 64);
    // The backend tag slug requires min_length 2; a single-character or
    // all-non-ASCII name would otherwise 422 the whole completion. Reject early.
    if (slug.length < 2) {
      customError = $_('onboarding.guided.custom_invalid');
      return;
    }
    customError = '';
    selected = new Map(selected).set(slug, {
      slug,
      name,
      category: customCategory,
      icon: null,
      color: null,
    });
    customName = '';
  }

  function isOffline(): boolean {
    return (
      (typeof navigator !== 'undefined' && !navigator.onLine) ||
      get(connectivity).serverReachable === false
    );
  }

  function back() {
    if (stepIndex > 0) stepIndex -= 1;
  }

  function next() {
    error = '';
    if (isLastStep) {
      void finish();
      return;
    }
    stepIndex += 1;
  }

  function buildTagPayload(): OnboardingTagInput[] {
    return selectedTags.map((tag) => {
      const habit = habitBySlug.get(tag.slug);
      return habit
        ? { ...tag, habit_type: habit.habit_type, target_frequency: habit.target_frequency }
        : tag;
    });
  }

  async function finish() {
    busy = true;
    error = '';
    try {
      // Persist the onboarding choices BEFORE the completion flag: otherwise a
      // failed preferences PATCH after a successful completeOnboarding() would
      // leave onboarding marked complete with the cycle/maturity choice lost and
      // no way back to this step. completeOnboarding is the atomic commit point.
      await updateUserPreferences({
        cycle_tracking_enabled: cycleEnabled,
        onboarding_maturity_intro_seen: true,
      });
      await completeOnboarding(buildTagPayload());
      await goto(OPEN_ENTRY_HOME_PATH);
    } catch (err) {
      // Offline-first fallback: stash the picks so the first entry sheet can
      // finalize onboarding once the API is reachable again, and still let the
      // user reach the entry. Online failures surface as a retryable error.
      if (isOffline()) {
        const userId = get(currentUser)?.id;
        if (userId) {
          writeOnboardingSuggestionStash({
            userId,
            suggestions: selectedTags,
            finalizeDeferred: true,
          });
        }
        await goto(OPEN_ENTRY_HOME_PATH);
        return;
      }
      error = err instanceof Error ? err.message : $_('error.generic');
    } finally {
      busy = false;
    }
  }
</script>

<svelte:head>
  <title>{$_('onboarding.guided.title')} - {$_('app.name')}</title>
</svelte:head>

<main class="onboarding-flow">
  <ScreenHeader title={$_('onboarding.guided.title')} visuallyHidden />

  {#if !checking}
    <div class="onboarding-flow__progress" aria-label={$_('onboarding.guided.progress')}>
      {#each steps as _step, item}
        <span class:active={item === stepIndex}></span>
      {/each}
      <small>{progressLabel}</small>
    </div>

    {#if error}
      <InlineAlert variant="error" message={error} />
    {/if}

    <Panel variant="bordered">
      {#if currentStep === 'maturity'}
        <h2 id="onboarding-maturity-title">{$_('onboarding.maturity_intro.title')}</h2>
        <MaturityExpectationContent headingId="onboarding-maturity-title" />
      {:else if currentStep === 'concepts'}
        <h2>{$_('onboarding.concepts.title')}</h2>
        <ConceptExplainer />
      {:else if currentStep === 'tags'}
        <h2>{$_('onboarding.guided.tags_title')}</h2>
        <p data-testid="onboarding-intro">{$_('onboarding.guided.intro')}</p>
        <p>{$_('onboarding.guided.tags_body')}</p>
        <p class="onboarding-flow__habit-hint" data-testid="onboarding-habit-hint">
          {$_('onboarding.guided.habit_hint')}
        </p>
        {#if loading}
          <p>{$_('tag.loading')}</p>
        {:else}
          <div class="onboarding-flow__groups">
            {#each groups as group}
              <section>
                <h3>{$_(`tag.category.${group.category}`)}</h3>
                <div class="onboarding-flow__chips">
                  {#each group.suggestions as tag}
                    <button
                      type="button"
                      class:active={selected.has(tag.slug)}
                      aria-pressed={selected.has(tag.slug)}
                      data-testid="onboarding-tag-suggestion"
                      on:click={() => toggleSuggestion(tag)}
                    >
                      {tagLabel(tag)}
                    </button>
                  {/each}
                </div>
              </section>
            {/each}
          </div>
        {/if}

        {#if customSelected.length}
          <div class="onboarding-flow__chips" data-testid="onboarding-custom-tags">
            {#each customSelected as tag}
              <button
                type="button"
                class="active"
                aria-pressed="true"
                on:click={() => toggleSuggestion(tag)}
              >
                {tag.name} ✕
              </button>
            {/each}
          </div>
        {/if}

        <div class="onboarding-flow__custom">
          <input
            class="input"
            bind:value={customName}
            placeholder={$_('onboarding.guided.custom')}
          />
          <select class="input" bind:value={customCategory}>
            {#each customCategories as category}
              <option value={category}>{$_(`tag.category.${category}`)}</option>
            {/each}
          </select>
          <Button variant="secondary" size="sm" on:click={addCustomTag}>
            {$_('onboarding.guided.add_tag')}
          </Button>
        </div>
        {#if customError}
          <p class="onboarding-flow__custom-error" role="alert">{customError}</p>
        {/if}
      {:else if currentStep === 'goals'}
        <h2>{$_('onboarding.goals.title')}</h2>
        <p>{$_('onboarding.goals.intro')}</p>
        <p class="onboarding-flow__habit-hint">{$_('onboarding.goals.optional_hint')}</p>
        <div class="onboarding-flow__goals" data-testid="onboarding-goals">
          {#each selectedTags as tag (tag.slug)}
            <div class="onboarding-flow__goal-row">
              <span class="onboarding-flow__goal-name">{tagLabel(tag)}</span>
              <select
                class="input"
                aria-label={$_('onboarding.goals.type_label', { values: { name: tagLabel(tag) } })}
                data-testid="onboarding-goal-type"
                value={habitTypeFor(tag.slug)}
                on:change={(e) =>
                  setHabitType(tag.slug, (e.currentTarget as HTMLSelectElement).value as HabitType)}
              >
                {#each HABIT_TYPES as ht}
                  <option value={ht}>{$_(`settings.tags.habit_${ht}`)}</option>
                {/each}
              </select>
              {#if habitTypeFor(tag.slug) !== 'none'}
                <label class="onboarding-flow__goal-freq">
                  <span aria-hidden="true">{$_('onboarding.goals.frequency_label')}</span>
                  <input
                    type="number"
                    class="input"
                    min="1"
                    max="7"
                    step="1"
                    aria-label={$_('onboarding.goals.frequency_aria', {
                      values: { name: tagLabel(tag) },
                    })}
                    value={habitFreqFor(tag.slug)}
                    on:input={(e) =>
                      setHabitFreq(
                        tag.slug,
                        Math.min(
                          7,
                          Math.max(
                            1,
                            Math.round(Number((e.currentTarget as HTMLInputElement).value) || 1)
                          )
                        )
                      )}
                  />
                </label>
              {/if}
            </div>
          {/each}
        </div>
      {:else if currentStep === 'summary'}
        <h2>{$_('onboarding.guided.summary_title')}</h2>
        <p>{$_('onboarding.guided.summary_body', { values: { count: selectedTags.length } })}</p>
        <div class="onboarding-flow__chips onboarding-flow__chips--summary">
          {#each selectedTags as tag}
            <span>{tagLabel(tag)}</span>
          {/each}
        </div>
      {:else if currentStep === 'cycle'}
        <CycleFunctionExplainer bind:enabled={cycleEnabled} />
      {/if}

      <div class="onboarding-flow__actions">
        {#if stepIndex > 0}
          <Button variant="ghost" on:click={back} disabled={busy}>
            {$_('onboarding.guided.back')}
          </Button>
        {/if}
        <Button variant="primary" on:click={next} loading={busy}>
          {isLastStep ? $_('onboarding.guided.start') : $_('onboarding.continue')}
        </Button>
      </div>
    </Panel>
  {/if}
</main>

<style>
  .onboarding-flow {
    width: min(100%, 44rem);
    margin: 0 auto;
    padding: var(--space-6) var(--space-4);
    display: flex;
    flex-direction: column;
    gap: var(--space-4);
  }

  .onboarding-flow h2,
  .onboarding-flow h3,
  .onboarding-flow p {
    margin: 0;
  }

  .onboarding-flow__habit-hint {
    color: var(--color-text-muted);
    font-size: var(--text-sm);
    line-height: 1.5;
    padding: var(--space-3);
    border-radius: var(--radius-sm);
    background: color-mix(in srgb, var(--color-primary) 8%, transparent);
    border: 1px solid color-mix(in srgb, var(--color-primary) 18%, transparent);
  }

  .onboarding-flow__progress,
  .onboarding-flow__actions,
  .onboarding-flow__custom {
    display: flex;
    align-items: center;
    gap: var(--space-2);
    flex-wrap: wrap;
  }

  .onboarding-flow__actions {
    justify-content: flex-end;
    margin-top: var(--space-4);
  }

  .onboarding-flow__progress span {
    width: 0.75rem;
    height: 0.75rem;
    border-radius: var(--radius-full);
    background: var(--color-border);
  }

  .onboarding-flow__progress span.active {
    background: var(--color-primary);
  }

  .onboarding-flow__groups {
    display: grid;
    gap: var(--space-4);
  }

  .onboarding-flow__chips {
    display: flex;
    gap: var(--space-2);
    overflow-x: auto;
    padding-block: var(--space-2);
  }

  .onboarding-flow__chips button,
  .onboarding-flow__chips span {
    min-height: 44px;
    border: 1px solid var(--color-border);
    border-radius: var(--radius-sm);
    background: var(--color-surface-2);
    color: var(--color-text);
    padding: var(--space-2) var(--space-3);
    white-space: nowrap;
  }

  .onboarding-flow__chips button.active {
    border-color: var(--color-primary);
    background: var(--color-primary-soft);
    color: var(--color-primary);
    font-weight: 650;
  }

  .onboarding-flow__chips--summary {
    flex-wrap: wrap;
    overflow: visible;
  }

  .onboarding-flow__custom-error {
    color: var(--color-error);
    font-size: var(--text-sm);
  }

  .onboarding-flow__goals {
    display: flex;
    flex-direction: column;
    gap: var(--space-3);
  }

  .onboarding-flow__goal-row {
    display: flex;
    align-items: center;
    gap: var(--space-2);
    flex-wrap: wrap;
    padding: var(--space-2) var(--space-3);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-sm);
  }

  .onboarding-flow__goal-name {
    flex: 1 1 8rem;
    font-weight: 600;
  }

  .onboarding-flow__goal-freq {
    display: flex;
    align-items: center;
    gap: var(--space-2);
    font-size: var(--text-sm);
    color: var(--color-text-muted);
  }

  .onboarding-flow__goal-freq input {
    width: 4rem;
  }
</style>
