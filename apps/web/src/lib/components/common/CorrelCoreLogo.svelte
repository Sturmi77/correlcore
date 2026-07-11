<script lang="ts">
  export let size = 64;
  export let title = 'CorrelCore';
</script>

<svg
  aria-label={title}
  viewBox="0 0 48 48"
  width={size}
  height={size}
  fill="none"
  xmlns="http://www.w3.org/2000/svg"
>
  <circle cx="24" cy="24" r="20" stroke="currentColor" stroke-width="3" opacity="0.2" />
  <path
    d="M24 4 A20 20 0 0 1 44 24"
    stroke="var(--color-primary)"
    stroke-width="3"
    stroke-linecap="round"
  />
  <path
    d="M16 26 Q24 34 32 26"
    stroke="var(--color-primary)"
    stroke-width="3"
    stroke-linecap="round"
    fill="none"
  />
  <circle cx="19" cy="20" r="1.5" fill="var(--color-primary)" />
  <circle cx="29" cy="20" r="1.5" fill="var(--color-primary)" />
</svg>
