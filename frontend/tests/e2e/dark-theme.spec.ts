import { expect, test } from '@playwright/test';
import { authenticate, preparePage } from './support/quality';

const giteaDarkTokens = {
  '--canvas': '#1e1f20',
  '--surface': '#191a1c',
  '--surface-raised': '#232528',
  '--surface-subtle': '#202124',
  '--surface-inset': '#161718',
  '--surface-header': '#1b1c1e',
  '--nav': '#18191b',
  '--selected': '#38393a',
  '--foreground': '#d2d4d8',
  '--foreground-bright': '#f8f8f8',
  '--foreground-secondary': '#c0c2c7',
  '--foreground-muted': '#969aa1',
  '--border': '#3f4248',
  '--border-strong': '#46494f',
  '--accent': '#4183c4',
  '--accent-text': '#679cd0',
  '--accent-hover': '#3876b3',
  '--accent-active': '#31699f',
  '--on-accent': '#161718',
  '--success': '#87ab63',
  '--warning': '#cc9903',
  '--danger': '#cc4848',
  '--danger-text': '#f85149',
  '--focus-ring': '#4183c4',
} as const;

test.describe('Gitea dark theme', () => {
  test.beforeEach(async ({ page }) => preparePage(page));

  test('uses the exact semantic palette and neutral admin surfaces', async ({
    context,
    page,
  }, testInfo) => {
    // Intentional project gate: exact palette values depend on the dark-theme fixture.
    test.skip(testInfo.project.name !== 'dark-desktop-chromium', 'Dark palette assertion');
    await authenticate(context);
    await page.goto('/admin/jobs');
    await expect(page.getByRole('heading', { name: 'Jobs', exact: true })).toBeVisible();
    await expect(
      page.getByRole('link', { name: 'Frontend Engineering Intern' }).first()
    ).toBeVisible();

    const tokens = await page.evaluate((names) => {
      const styles = getComputedStyle(document.documentElement);
      return Object.fromEntries(names.map((name) => [name, styles.getPropertyValue(name).trim()]));
    }, Object.keys(giteaDarkTokens));
    expect(tokens).toEqual(giteaDarkTokens);

    await page.mouse.move(0, 0);
    const backgrounds = await page.evaluate(() => {
      const activeNavItem = document.querySelector<HTMLElement>(
        'nav[aria-label="Admin navigation"] a[aria-current="page"]'
      );
      return {
        page: getComputedStyle(document.documentElement).backgroundColor,
        navigation: getComputedStyle(document.querySelector('aside')!).backgroundColor,
        selected: getComputedStyle(activeNavItem!).backgroundColor,
      };
    });
    const tableRow = await page
      .locator('tbody tr:visible')
      .first()
      .evaluate((row) => getComputedStyle(row).backgroundColor);
    expect(backgrounds).toEqual({
      page: 'rgb(30, 31, 32)',
      navigation: 'rgb(24, 25, 27)',
      selected: 'rgb(56, 57, 58)',
    });
    expect(tableRow).toBe('rgb(22, 23, 24)');
  });
});
