<script lang="ts">
  import { _ } from 'svelte-i18n';

  /**
   * Canonical Tag / Habit / Symptom (+ cycle day) definitions (#541). Reused
   * before the onboarding tag step so users understand the vocabulary before they
   * pick tags, and behind a "?" where these are managed (Settings → Tags). The
   * wording is the locked version from the M10.2 plan (§1.1 / E5) — keep the copy
   * here in sync with `onboarding.concepts.*` only.
   */
  const concepts = ['tag', 'habit', 'symptom', 'cycle'] as const;
</script>

<section
  class="concept-explainer"
  data-testid="concept-explainer"
  aria-labelledby="concept-explainer-title"
>
  <h3 id="concept-explainer-title" class="concept-explainer__title">
    {$_('onboarding.concepts.title')}
  </h3>
  <p class="concept-explainer__intro">{$_('onboarding.concepts.intro')}</p>
  <dl class="concept-explainer__list">
    {#each concepts as concept}
      <div class="concept-explainer__item" data-testid={`concept-${concept}`}>
        <dt>{$_(`onboarding.concepts.${concept}_term`)}</dt>
        <dd>{$_(`onboarding.concepts.${concept}_body`)}</dd>
      </div>
    {/each}
  </dl>
  <p class="concept-explainer__footer">{$_('onboarding.concepts.footer')}</p>
</section>

<style>
  .concept-explainer {
    display: flex;
    flex-direction: column;
    gap: var(--space-2);
    padding: var(--space-4);
    border-radius: var(--radius-md);
    border: 1px solid color-mix(in srgb, var(--color-primary) 18%, transparent);
    background: color-mix(in srgb, var(--color-primary) 6%, transparent);
  }

  .concept-explainer__title {
    margin: 0;
    font-size: var(--text-sm);
    font-weight: 650;
  }

  .concept-explainer__intro {
    margin: 0;
    font-size: var(--text-sm);
    color: var(--color-text-muted);
    line-height: 1.5;
  }

  .concept-explainer__list {
    display: flex;
    flex-direction: column;
    gap: var(--space-3);
    margin: var(--space-1) 0 0;
  }

  .concept-explainer__item {
    display: flex;
    flex-direction: column;
    gap: 0.15rem;
  }

  .concept-explainer__item dt {
    font-size: var(--text-sm);
    font-weight: 650;
    color: var(--color-text);
  }

  .concept-explainer__item dd {
    margin: 0;
    font-size: var(--text-sm);
    line-height: 1.5;
    color: var(--color-text-muted);
  }

  .concept-explainer__footer {
    margin: var(--space-1) 0 0;
    font-size: var(--text-xs);
    color: var(--color-text-faint);
  }
</style>
