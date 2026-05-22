<script lang="ts">
  import { _ } from 'svelte-i18n';
  import { evaluatePassword } from '$lib/utils/passwordStrength';

  export let password: string = '';

  $: strength = evaluatePassword(password);

  const labels = ['empty', 'very_weak', 'weak', 'good', 'strong'] as const;
</script>

{#if password.length > 0}
  <div class="strength" aria-live="polite">
    <div class="bars" aria-hidden="true">
      {#each [0, 1, 2, 3] as i}
        <span class="bar" class:filled={strength.score > i} data-score={strength.score}></span>
      {/each}
    </div>
    <span class="label" data-score={strength.score}>
      {$_(`auth.register.strength_${labels[strength.score]}`)}
    </span>
  </div>
{/if}

<style>
  .strength {
    display: flex;
    align-items: center;
    gap: var(--space-3);
    font-size: var(--text-xs);
  }

  .bars {
    display: flex;
    gap: 4px;
    flex: 1;
  }

  .bar {
    flex: 1;
    height: 4px;
    border-radius: 2px;
    background: var(--color-surface-offset);
    transition: background var(--transition-interactive);
  }

  .bar.filled[data-score='1'] {
    background: var(--color-error);
  }
  .bar.filled[data-score='2'] {
    background: var(--color-warning);
  }
  .bar.filled[data-score='3'] {
    background: var(--color-success);
  }
  .bar.filled[data-score='4'] {
    background: var(--color-ms-primary);
  }

  .label {
    flex-shrink: 0;
    font-weight: 500;
    opacity: 0.85;
  }
</style>
