<script lang="ts">
  import Button, { type ButtonSize, type ButtonVariant } from './Button.svelte';

  export let href: string | undefined = undefined;
  export let type: 'button' | 'submit' | 'reset' = 'button';
  export let variant: ButtonVariant = 'ghost';
  export let size: ButtonSize = 'md';
  export let ariaLabel: string;
  export let title: string | undefined = undefined;
  export let disabled = false;
  export let loading = false;
  export let className = '';
</script>

<Button
  {...$$restProps}
  {href}
  {type}
  {variant}
  {size}
  {disabled}
  {loading}
  {className}
  iconOnly
  aria-label={ariaLabel}
  title={title ?? ariaLabel}
  on:click
>
  <slot />
</Button>
