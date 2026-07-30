import { expect, test } from '@playwright/test';

test('home stress bars use inverted widths (lower stress = wider bar)', async ({ page }) => {
  await page.addInitScript(() => {
    localStorage.setItem('dev_mode_enabled', 'true');
    localStorage.setItem('dev_force_viz', 'true');
  });

  await page.route('**/api/v1/auth/me', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        id: 'user-1',
        email: 'stress@example.com',
        display_name: 'Stress',
        is_verified: true,
      }),
    });
  });

  await page.route('**/api/v1/auth/refresh', async (route) => {
    await route.fulfill({ status: 204, body: '' });
  });

  await page.route('**/api/v1/insights**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        insight_maturity: {
          phase: 'provisional',
          phase_index: 3,
          current_entries: 21,
          next_phase_at: 30,
          next_phase_label: 'Robust Insights',
          entries_until_next: 9,
          user_message_key: 'maturity.provisional.description',
        },
        insights: [],
      }),
    });
  });

  await page.route('**/api/v1/entries**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([]),
    });
  });

  await page.route('**/api/v1/dashboard**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        entry_count: 21,
        insight_tier: 'preliminary',
        confidence_score: 0.48,
        work_context_summary: [
          {
            work_context: 'office',
            entry_count: 9,
            mood_avg: 3.4,
            energy_avg: 3.2,
            stress_avg: 3.6,
          },
          {
            work_context: 'homeoffice',
            entry_count: 8,
            mood_avg: 3.9,
            energy_avg: 3.7,
            stress_avg: 2.8,
          },
          {
            work_context: 'vacation',
            entry_count: 4,
            mood_avg: 4.2,
            energy_avg: 3.8,
            stress_avg: 2.2,
          },
        ],
      }),
    });
  });

  await page.route('**/api/v1/user/preferences**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        user_id: 'user-1',
        analytics_enabled: true,
        onboarding_retro_completed: true,
        onboarding_profile_completed: true,
        onboarding_maturity_intro_seen: true,
        dismissed_insight_keys: [],
        reached_milestone_keys: [],
        created_at: '2026-01-01T00:00:00Z',
        updated_at: '2026-01-01T00:00:00Z',
      }),
    });
  });

  await page.goto('/');

  await page.getByTestId('home-work-context-metric-stress').click();

  const bars = page.locator('.daily-brief__work-context-bar');
  await expect(bars).toHaveCount(3);

  const widths = await bars.evaluateAll((nodes) =>
    nodes.map((node) => {
      const style = (node as HTMLElement).style.getPropertyValue('--bar-width');
      return parseFloat(style);
    })
  );

  const labels = await page.locator('.daily-brief__work-context-row strong').allTextContents();

  // vacation 2.2 -> display 3.8 -> 76%; office 3.6 -> 2.4 -> 48%; homeoffice 2.8 -> 3.2 -> 64%
  expect(Math.max(...widths)).toBeCloseTo(76, 0);
  expect(Math.min(...widths)).toBeCloseTo(48, 0);

  const vacationIndex = labels.findIndex((t) => t.includes('2.2'));
  const officeIndex = labels.findIndex((t) => t.includes('3.6'));
  const homeofficeIndex = labels.findIndex((t) => t.includes('2.8'));
  expect(vacationIndex).toBeGreaterThanOrEqual(0);
  expect(officeIndex).toBeGreaterThanOrEqual(0);
  expect(widths[vacationIndex]).toBeGreaterThan(widths[officeIndex]);

  const rowData = await page.locator('.daily-brief__work-context-row').evaluateAll((rows) =>
    rows.map((row) => ({
      highlight: row.getAttribute('data-highlight'),
      metricColor: (
        row.querySelector('.daily-brief__work-context-bar') as HTMLElement
      )?.style.getPropertyValue('--bar-metric-color'),
      barColor: getComputedStyle(
        row.querySelector('.daily-brief__work-context-bar') as Element
      ).getPropertyValue('--bar-color'),
    }))
  );

  expect(rowData[vacationIndex].highlight).toBe('high');
  expect(rowData[officeIndex].highlight).toBe('low');
  expect(rowData[homeofficeIndex].highlight).toBe('none');

  // Worst stress uses metric red; neutral uses primary; best uses success green.
  expect(rowData[officeIndex].barColor).toMatch(/metric-stress|239,\s*68,\s*68|ef4444/i);
  expect(rowData[homeofficeIndex].metricColor).toContain('primary');
  expect(rowData[vacationIndex].barColor).toMatch(/success|22,\s*163,\s*74|16a34a/i);
});
