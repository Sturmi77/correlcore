<script lang="ts">
  import { goto } from '$app/navigation';
  import { _ } from 'svelte-i18n';
  import { createEntryBatch, type EntryCreatePayload } from '$lib/api/entries';
  import { updateUserPreferences } from '$lib/api/preferences';
  import { localIsoDate } from '$lib/utils/home';
  import { shiftIsoDate } from '$lib/utils/streak';

  const today = localIsoDate(new Date());
  const days = Array.from({ length: 7 }, (_, index) => shiftIsoDate(today, -(index + 1)));
  let moods: Record<string, number> = {};
  let saving = false;
  let error = '';

  async function complete(skip = false): Promise<void> {
    saving = true;
    error = '';
    try {
      if (!skip) {
        const entries: EntryCreatePayload[] = Object.entries(moods).map(([entry_date, mood]) => ({
          entry_date,
          mood_score: mood,
          energy: 3,
          stress: 3,
          source: 'retrospective',
          work_context: 'homeoffice',
        }));
        if (entries.length) await createEntryBatch({ entries });
      }
      await updateUserPreferences({ onboarding_retro_completed: true });
      void goto('/onboarding/profile');
    } catch (err) {
      error = err instanceof Error ? err.message : $_('error.generic');
    } finally {
      saving = false;
    }
  }
</script>

<svelte:head>
  <title>{$_('onboarding.retro.title')} - {$_('app.name')}</title>
</svelte:head>

<main class="onboarding">
  <h1>{$_('onboarding.retro.title')}</h1>
  <p>{$_('onboarding.retro.body')}</p>

  {#if error}<p class="onboarding__error">{error}</p>{/if}

  <div class="onboarding__days">
    {#each days as day}
      <section class="onboarding__day">
        <h2>{day}</h2>
        <div class="onboarding__moods">
          {#each [1, 2, 3, 4, 5] as mood}
            <button
              type="button"
              class:active={moods[day] === mood}
              on:click={() => (moods = { ...moods, [day]: mood })}
            >
              {mood}
            </button>
          {/each}
        </div>
      </section>
    {/each}
  </div>

  <footer class="onboarding__actions">
    <button
      class="btn btn-sm variant-ghost-surface"
      type="button"
      disabled={saving}
      on:click={() => complete(true)}
    >
      {$_('onboarding.skip')}
    </button>
    <button
      class="btn btn-sm btn--primary"
      type="button"
      disabled={saving}
      on:click={() => complete(false)}
    >
      {$_('onboarding.continue')}
    </button>
  </footer>
</main>

<style>
  .onboarding {
    display: flex;
    flex-direction: column;
    gap: 1rem;
    padding: 1rem 0 2rem;
  }

  .onboarding h1,
  .onboarding p,
  .onboarding__day h2 {
    margin: 0;
  }

  .onboarding__days {
    display: grid;
    gap: 0.65rem;
  }

  .onboarding__day {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 1rem;
    padding: 0.75rem;
    border: 1px solid var(--color-border-chart);
    border-radius: 0.45rem;
  }

  .onboarding__day h2 {
    font-size: 0.9rem;
  }

  .onboarding__moods,
  .onboarding__actions {
    display: flex;
    gap: 0.45rem;
  }

  .onboarding__moods button {
    width: 2.75rem;
    height: 2.75rem;
    border-radius: 999px;
    border: 1px solid var(--color-border);
    background: transparent;
  }

  .onboarding__moods button.active {
    background: var(--color-primary);
    color: var(--color-text-inverse);
  }

  .onboarding__actions {
    justify-content: flex-end;
  }

  .onboarding__error {
    color: var(--color-error);
  }

  @media (max-width: 430px) {
    .onboarding__day {
      align-items: stretch;
      flex-direction: column;
    }

    .onboarding__moods {
      justify-content: space-between;
    }

    .onboarding__actions > :global(*) {
      flex: 1;
      min-height: 44px;
    }
  }
</style>
