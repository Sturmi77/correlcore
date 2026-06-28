import { readdirSync, readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { describe, expect, it } from 'vitest';

const templateDir = resolve('figma/components');

describe('Code Connect template contract', () => {
  it('starts every template with its Figma URL metadata', () => {
    const templates = readdirSync(templateDir).filter((name) => name.endsWith('.figma.ts'));

    expect(templates.length).toBeGreaterThan(0);
    for (const template of templates) {
      const [firstLine] = readFileSync(resolve(templateDir, template), 'utf8').split(/\r?\n/);
      expect(firstLine, template).toMatch(/^\/\/ url=https:\/\/www\.figma\.com\//);
    }
  });

  it('emits a valid ScaleSlider value prop', () => {
    const source = readFileSync(resolve(templateDir, 'ScaleSlider.figma.ts'), 'utf8');

    expect(source).toContain('value={${Number(value) || 3}}');
    expect(source).not.toContain('bind:value={${Number(value) || 3}}');
  });

  it('maps MetricCard to an importable implementation', () => {
    const source = readFileSync(resolve(templateDir, 'MetricCard.figma.ts'), 'utf8');
    const component = resolve('src/lib/components/home/MetricCard.svelte');

    expect(source).toContain('// source=apps/web/src/lib/components/home/MetricCard.svelte');
    expect(source).toContain('import MetricCard from "$lib/components/home/MetricCard.svelte";');
    expect(readFileSync(component, 'utf8')).toContain('export let metric');
  });

  it('maps MobileInsightLead to an importable implementation', () => {
    const source = readFileSync(resolve(templateDir, 'MobileInsightLead.figma.ts'), 'utf8');
    const component = resolve('src/lib/components/insights/MobileInsightLead.svelte');

    expect(source).toContain(
      '// source=apps/web/src/lib/components/insights/MobileInsightLead.svelte'
    );
    expect(source).toContain(
      'import MobileInsightLead from "$lib/components/insights/MobileInsightLead.svelte";'
    );
    expect(readFileSync(component, 'utf8')).toContain('export let insight');
  });
});
