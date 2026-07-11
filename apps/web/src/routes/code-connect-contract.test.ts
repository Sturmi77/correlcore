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

  it('maps InsightCard to an importable implementation', () => {
    const source = readFileSync(resolve(templateDir, 'InsightCard.figma.ts'), 'utf8');
    const component = resolve('src/lib/components/insights/InsightCard.svelte');

    expect(source).toContain('// source=apps/web/src/lib/components/insights/InsightCard.svelte');
    expect(source).toContain(
      'import InsightCard from "$lib/components/insights/InsightCard.svelte";'
    );
    expect(readFileSync(component, 'utf8')).toContain('export let insight');
  });

  it('maps InsightStageHeader to an importable implementation', () => {
    const source = readFileSync(resolve(templateDir, 'InsightStageHeader.figma.ts'), 'utf8');
    const component = resolve('src/lib/components/insights/InsightStageHeader.svelte');

    expect(source).toContain(
      '// source=apps/web/src/lib/components/insights/InsightStageHeader.svelte'
    );
    expect(source).toContain(
      'import InsightStageHeader from "$lib/components/insights/InsightStageHeader.svelte";'
    );
    expect(readFileSync(component, 'utf8')).toContain('export let maturity');
  });

  it('maps TagChip to TagPicker chip usage', () => {
    const source = readFileSync(resolve(templateDir, 'TagChip.figma.ts'), 'utf8');
    const component = resolve('src/lib/components/entries/TagPicker.svelte');

    expect(source).toContain('// source=apps/web/src/lib/components/entries/TagPicker.svelte');
    expect(source).toContain('import TagPicker from "$lib/components/entries/TagPicker.svelte";');
    expect(readFileSync(component, 'utf8')).toContain('export let selected');
  });

  it('maps FormField to TagPicker form usage', () => {
    const source = readFileSync(resolve(templateDir, 'FormField.figma.ts'), 'utf8');
    const component = resolve('src/lib/components/entries/TagPicker.svelte');

    expect(source).toContain('// source=apps/web/src/lib/components/entries/TagPicker.svelte');
    expect(source).toContain('import TagPicker from "$lib/components/entries/TagPicker.svelte";');
    expect(readFileSync(component, 'utf8')).toContain('export let selected');
  });

  it('maps MobileTrendsSummary to an importable implementation', () => {
    const source = readFileSync(resolve(templateDir, 'MobileTrendsSummary.figma.ts'), 'utf8');
    const component = resolve('src/lib/components/trends/MobileTrendsSummary.svelte');

    expect(source).toContain(
      '// source=apps/web/src/lib/components/trends/MobileTrendsSummary.svelte'
    );
    expect(source).toContain(
      'import MobileTrendsSummary from "$lib/components/trends/MobileTrendsSummary.svelte";'
    );
    expect(readFileSync(component, 'utf8')).toContain('export let points');
  });

  it('maps InsightMatrix to an importable implementation', () => {
    const source = readFileSync(resolve(templateDir, 'InsightMatrix.figma.ts'), 'utf8');
    const component = resolve('src/lib/components/insights/InsightMatrix.svelte');

    expect(source).toContain('// source=apps/web/src/lib/components/insights/InsightMatrix.svelte');
    expect(source).toContain(
      'import InsightMatrix from "$lib/components/insights/InsightMatrix.svelte";'
    );
    expect(readFileSync(component, 'utf8')).toContain('export let insights');
  });

  it('maps TagGroupsSection to an importable implementation', () => {
    const source = readFileSync(resolve(templateDir, 'TagGroupsSection.figma.ts'), 'utf8');
    const component = resolve('src/lib/components/insights/TagGroupsSection.svelte');

    expect(source).toContain(
      '// source=apps/web/src/lib/components/insights/TagGroupsSection.svelte'
    );
    expect(source).toContain(
      'import TagGroupsSection from "$lib/components/insights/TagGroupsSection.svelte";'
    );
    expect(readFileSync(component, 'utf8')).toContain('export let data');
  });

  it('maps SymptomCooccurrenceDetailSheet to an importable implementation', () => {
    const source = readFileSync(
      resolve(templateDir, 'SymptomCooccurrenceDetailSheet.figma.ts'),
      'utf8'
    );
    const component = resolve(
      'src/lib/components/insights/symptoms/SymptomCooccurrenceDetailSheet.svelte'
    );

    expect(source).toContain(
      'import SymptomCooccurrenceDetailSheet from "$lib/components/insights/symptoms/SymptomCooccurrenceDetailSheet.svelte";'
    );
    expect(readFileSync(component, 'utf8')).toContain('export let open');
  });

  it('maps SymptomCooccurrenceHeatmap to an importable implementation', () => {
    const source = readFileSync(
      resolve(templateDir, 'SymptomCooccurrenceHeatmap.figma.ts'),
      'utf8'
    );
    const component = resolve(
      'src/lib/components/insights/symptoms/SymptomCooccurrenceHeatmap.svelte'
    );

    expect(source).toContain(
      '// source=apps/web/src/lib/components/insights/symptoms/SymptomCooccurrenceHeatmap.svelte'
    );
    expect(source).toContain(
      'import SymptomCooccurrenceHeatmap from "$lib/components/insights/symptoms/SymptomCooccurrenceHeatmap.svelte";'
    );
    expect(readFileSync(component, 'utf8')).toContain('export let data');
  });

  it('maps TagCooccurrenceHeatmap to an importable implementation', () => {
    const source = readFileSync(resolve(templateDir, 'TagCooccurrenceHeatmap.figma.ts'), 'utf8');
    const component = resolve('src/lib/components/insights/TagCooccurrenceHeatmap.svelte');

    expect(source).toContain(
      '// source=apps/web/src/lib/components/insights/TagCooccurrenceHeatmap.svelte'
    );
    expect(source).toContain(
      'import TagCooccurrenceHeatmap from "$lib/components/insights/TagCooccurrenceHeatmap.svelte";'
    );
    expect(readFileSync(component, 'utf8')).toContain('export let data');
  });

  it('maps EntryHistorySheet to an importable implementation', () => {
    const source = readFileSync(resolve(templateDir, 'EntryHistorySheet.figma.ts'), 'utf8');
    const component = resolve('src/lib/components/trends/EntryHistorySheet.svelte');

    expect(source).toContain(
      '// source=apps/web/src/lib/components/trends/EntryHistorySheet.svelte'
    );
    expect(source).toContain(
      'import EntryHistorySheet from "$lib/components/trends/EntryHistorySheet.svelte";'
    );
    expect(readFileSync(component, 'utf8')).toContain('export let open');
  });

  it('maps SymptomAnalyticsSection to an importable implementation', () => {
    const source = readFileSync(resolve(templateDir, 'SymptomAnalyticsSection.figma.ts'), 'utf8');
    const component = resolve(
      'src/lib/components/insights/symptoms/SymptomAnalyticsSection.svelte'
    );

    expect(source).toContain(
      '// source=apps/web/src/lib/components/insights/symptoms/SymptomAnalyticsSection.svelte'
    );
    expect(source).toContain(
      'import SymptomAnalyticsSection from "$lib/components/insights/symptoms/SymptomAnalyticsSection.svelte";'
    );
    expect(readFileSync(component, 'utf8')).toContain('export let heatmap');
  });
});
