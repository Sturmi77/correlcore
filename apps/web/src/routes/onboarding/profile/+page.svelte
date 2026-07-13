<script lang="ts">
  import { goto } from '$app/navigation';
  import { _ } from 'svelte-i18n';
  import { upsertUserProfile, type UserProfilePayload } from '$lib/api/profile';
  import { updateUserPreferences } from '$lib/api/preferences';
  import ScreenHeader from '$lib/components/common/ScreenHeader.svelte';
  import previews from '$lib/data/insight_previews.json';

  let profile: UserProfilePayload = {};
  let submitted = false;
  let saving = false;
  let error = '';

  function matches(match: Record<string, string>): boolean {
    return Object.entries(match).every(
      ([key, value]) => profile[key as keyof UserProfilePayload] === value
    );
  }

  $: selectedPreviews = previews
    .filter((preview) => matches(preview.match as Record<string, string>))
    .slice(0, 3);
  $: shownPreviews = selectedPreviews.length ? selectedPreviews : previews.slice(-1);

  async function save(skip = false): Promise<void> {
    saving = true;
    error = '';
    try {
      if (!skip) {
        await upsertUserProfile(profile);
        submitted = true;
      }
      await updateUserPreferences({ onboarding_profile_completed: true });
      if (skip) void goto('/');
    } catch (err) {
      error = err instanceof Error ? err.message : $_('error.generic');
    } finally {
      saving = false;
    }
  }
</script>

<svelte:head>
  <title>{$_('onboarding.profile.title')} - {$_('app.name')}</title>
</svelte:head>

<main class="profile-onboarding">
  <ScreenHeader title={$_('onboarding.profile.title')} visuallyHidden />

  <h2 class="profile-onboarding__heading">{$_('onboarding.profile.title')}</h2>
  <p>{$_('onboarding.profile.body')}</p>

  {#if error}<p class="profile-onboarding__error">{error}</p>{/if}

  <section class="profile-onboarding__questions">
    <label>
      {$_('onboarding.profile.sleep')}
      <select bind:value={profile.sleep_hours_typical}>
        <option value={undefined}>{$_('onboarding.skip_question')}</option>
        <option value="5h">5h</option>
        <option value="6h">6h</option>
        <option value="7h">7h</option>
        <option value="8h">8h</option>
        <option value="9h_plus">9h+</option>
      </select>
    </label>
    <label>
      {$_('onboarding.profile.work')}
      <select bind:value={profile.work_context_typical}>
        <option value={undefined}>{$_('onboarding.skip_question')}</option>
        <option value="office">{$_('onboarding.profile.work_office')}</option>
        <option value="hybrid">{$_('onboarding.profile.work_hybrid')}</option>
        <option value="remote">{$_('onboarding.profile.work_remote')}</option>
        <option value="other">{$_('onboarding.profile.other')}</option>
      </select>
    </label>
    <label>
      {$_('onboarding.profile.sport')}
      <select bind:value={profile.sport_frequency}>
        <option value={undefined}>{$_('onboarding.skip_question')}</option>
        <option value="rarely">{$_('onboarding.profile.sport_rarely')}</option>
        <option value="1_2_week">1-2x</option>
        <option value="3_4_week">3-4x</option>
        <option value="daily">{$_('onboarding.profile.sport_daily')}</option>
      </select>
    </label>
    <label>
      {$_('onboarding.profile.curiosity')}
      <select bind:value={profile.insight_curiosity}>
        <option value={undefined}>{$_('onboarding.skip_question')}</option>
        <option value="work_life">{$_('onboarding.profile.curiosity_work')}</option>
        <option value="energy_sleep">{$_('onboarding.profile.curiosity_sleep')}</option>
        <option value="habits_sport">{$_('onboarding.profile.curiosity_sport')}</option>
        <option value="wellbeing">{$_('onboarding.profile.curiosity_wellbeing')}</option>
      </select>
    </label>
  </section>

  <footer class="profile-onboarding__actions">
    <button
      class="btn btn-sm variant-ghost-surface"
      type="button"
      disabled={saving}
      on:click={() => save(true)}
    >
      {$_('onboarding.skip')}
    </button>
    <button
      class="btn btn-sm btn--primary"
      type="button"
      disabled={saving}
      on:click={() => save(false)}
    >
      {$_('onboarding.profile.show_previews')}
    </button>
  </footer>

  {#if submitted}
    <section class="profile-onboarding__previews">
      <h2>{$_('onboarding.profile.preview_heading')}</h2>
      {#each shownPreviews as preview}
        <article>
          <strong>{$_('onboarding.profile.preview_label')}</strong>
          <p>{preview.preview_text}</p>
          <small>{preview.source_label}</small>
        </article>
      {/each}
      <a class="btn btn-sm btn--secondary" href="/">{$_('onboarding.finish')}</a>
    </section>
  {/if}
</main>

<style>
  .profile-onboarding {
    display: flex;
    flex-direction: column;
    gap: 1rem;
    padding: 1rem 0 2rem;
  }

  .profile-onboarding h2,
  .profile-onboarding p {
    margin: 0;
  }

  .profile-onboarding__heading {
    margin: 0;
    font-size: var(--text-xl);
    font-weight: 700;
  }

  .profile-onboarding__questions,
  .profile-onboarding__previews {
    display: grid;
    gap: 0.75rem;
  }

  .profile-onboarding label,
  .profile-onboarding__previews article {
    display: grid;
    gap: 0.35rem;
    padding: 0.75rem;
    border: 1px solid var(--color-border-chart);
    border-radius: 0.45rem;
  }

  .profile-onboarding select {
    min-height: 2.75rem;
  }

  .profile-onboarding__actions {
    display: flex;
    justify-content: flex-end;
    gap: 0.5rem;
  }

  .profile-onboarding__previews small,
  .profile-onboarding__error {
    color: var(--color-text-muted);
  }

  @media (max-width: 430px) {
    .profile-onboarding__actions {
      align-items: stretch;
      flex-direction: column-reverse;
    }

    .profile-onboarding__actions button,
    .profile-onboarding__previews a {
      min-height: 44px;
    }
  }
</style>
