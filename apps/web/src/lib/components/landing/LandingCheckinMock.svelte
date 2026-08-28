<script lang="ts">
  /**
   * Static 60-second check-in shot for the marketing hero (#735 I2).
   * Not interactive — the parent product frame is inert + aria-hidden.
   */
  import { _ } from 'svelte-i18n';

  const scales = [
    { key: 'mood', value: 4, tone: 'mood' },
    { key: 'energy', value: 3, tone: 'energy' },
    { key: 'stress', value: 2, tone: 'stress' },
    { key: 'sleep', value: 4, tone: 'sleep' },
  ] as const;

  const tags = [
    { key: 'walk', tone: 'energy' },
    { key: 'meetings', tone: 'mood' },
    { key: 'caffeine', tone: 'gold' },
  ] as const;
</script>

<div class="checkin" data-testid="landing-checkin-mock">
  <header class="checkin__header">
    <span class="checkin__date">{$_('landing.checkin.today')}</span>
    <span class="checkin__hint">{$_('landing.checkin.duration')}</span>
  </header>

  <ul class="checkin__scales">
    {#each scales as scale (scale.key)}
      <li class="checkin__scale" data-tone={scale.tone}>
        <span class="checkin__label">{$_(`landing.checkin.${scale.key}`)}</span>
        <span class="checkin__dots" aria-hidden="true">
          {#each [1, 2, 3, 4, 5] as n}
            <span class="checkin__dot" class:is-on={n <= scale.value}></span>
          {/each}
        </span>
        <span class="checkin__value">{scale.value}</span>
      </li>
    {/each}
  </ul>

  <div class="checkin__chips">
    <span class="checkin__chips-label">{$_('landing.checkin.tags')}</span>
    <ul class="checkin__chip-row">
      {#each tags as tag (tag.key)}
        <li class="checkin__chip is-on" data-tone={tag.tone}>
          {$_(`landing.demo.${tag.key}`)}
        </li>
      {/each}
    </ul>
  </div>

  <div class="checkin__chips">
    <span class="checkin__chips-label">{$_('landing.checkin.symptoms')}</span>
    <ul class="checkin__chip-row">
      <li class="checkin__chip is-on" data-tone="stress">
        {$_('landing.demo.headache')}
      </li>
      <li class="checkin__chip">
        {$_('landing.demo.fatigue')}
      </li>
    </ul>
  </div>
</div>

<style>
  .checkin {
    display: flex;
    flex-direction: column;
    gap: var(--space-3);
  }

  .checkin__header {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    gap: var(--space-3);
  }

  .checkin__date {
    font-size: var(--text-sm);
    font-weight: 600;
  }

  .checkin__hint {
    font-size: var(--text-2xs);
    color: var(--color-text-faint);
  }

  .checkin__scales {
    list-style: none;
    margin: 0;
    padding: 0;
    display: flex;
    flex-direction: column;
    gap: var(--space-2);
  }

  .checkin__scale {
    display: grid;
    grid-template-columns: minmax(4.5rem, 7rem) 1fr auto;
    align-items: center;
    gap: var(--space-2);
  }

  .checkin__label,
  .checkin__chips-label {
    font-size: var(--text-xs);
    color: var(--color-text-muted);
  }

  .checkin__dots {
    display: flex;
    gap: 0.28rem;
  }

  .checkin__dot {
    width: 0.55rem;
    height: 0.55rem;
    border-radius: var(--radius-full);
    background: var(--color-border);
  }

  .checkin__dot.is-on {
    background: var(--tone, var(--color-primary));
  }

  .checkin__value {
    font-size: var(--text-xs);
    font-variant-numeric: tabular-nums;
    font-weight: 600;
    min-width: 1ch;
  }

  .checkin__chips {
    display: flex;
    flex-direction: column;
    gap: var(--space-1);
  }

  .checkin__chip-row {
    list-style: none;
    margin: 0;
    padding: 0;
    display: flex;
    flex-wrap: wrap;
    gap: var(--space-1);
  }

  .checkin__chip {
    padding: 0.2rem 0.55rem;
    border: 1px solid var(--color-border);
    border-radius: var(--radius-full);
    font-size: var(--text-2xs);
    color: var(--color-text-muted);
  }

  .checkin__chip.is-on {
    border-color: color-mix(in srgb, var(--tone, var(--color-primary)) 45%, var(--color-border));
    background: color-mix(in srgb, var(--tone, var(--color-primary)) 14%, transparent);
    color: var(--color-text);
    font-weight: 600;
  }

  .checkin__scale[data-tone='mood'],
  .checkin__chip[data-tone='mood'] {
    --tone: var(--color-metric-mood);
  }
  .checkin__scale[data-tone='energy'],
  .checkin__chip[data-tone='energy'] {
    --tone: var(--color-metric-energy);
  }
  .checkin__scale[data-tone='stress'],
  .checkin__chip[data-tone='stress'] {
    --tone: var(--color-metric-stress);
  }
  .checkin__scale[data-tone='sleep'] {
    --tone: var(--color-metric-sleep);
  }
  .checkin__chip[data-tone='gold'] {
    --tone: var(--color-gold);
  }
</style>
