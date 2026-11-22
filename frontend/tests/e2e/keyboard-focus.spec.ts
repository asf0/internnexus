import { expect, test } from '@playwright/test';
import { authenticate, preparePage } from './support/quality';

const primaryProjects = new Set(['desktop-chromium', 'mobile-chromium']);
const adminProjects = new Set(['desktop-chromium', 'mobile-chromium', 'tablet-portrait-chromium']);

test.describe('representative keyboard and focus behavior', () => {
  test.beforeEach(async ({ page }) => preparePage(page));

  test('public search and filter controls operate from the keyboard', async ({
    page,
  }, testInfo) => {
    // Intentional project gate: these widths cover both responsive control layouts.
    test.skip(!primaryProjects.has(testInfo.project.name), 'Covered at desktop and phone widths');
    await page.goto('/');

    const search = page.getByPlaceholder('Search jobs...');
    await search.focus();
    await expect(search).toBeFocused();
    await search.fill('frontend');
    await search.press('Enter');
    await expect(page).toHaveURL(/(?:\?|&)search=frontend(?:&|$)/);

    const filters = page.getByRole('button', { name: 'Filters' });
    await filters.focus();
    await expect(filters).toBeFocused();
    await filters.press('Enter');

    const company = page.getByRole('button', { name: 'Company' });
    await expect(company).toBeVisible();
    await company.focus();
    await company.press('Enter');
    await expect(page.getByPlaceholder('Search...').first()).toBeFocused();
    await page.keyboard.press('Escape');
    await expect(company).toHaveAttribute('aria-expanded', 'false');
  });

  test('settings save and back controls preserve focus and keyboard activation', async ({
    context,
    page,
  }, testInfo) => {
    // Intentional project gate: settings controls do not vary across viewport projects.
    test.skip(testInfo.project.name !== 'desktop-chromium', 'One viewport is sufficient');
    await authenticate(context);
    await page.goto('/');
    await page.goto('/settings');

    const name = page.getByRole('textbox', { name: 'Full Name' });
    await name.focus();
    await expect(name).toBeFocused();
    await name.fill('Alex Keyboard');

    const save = page.getByRole('button', { name: 'Save All Changes' });
    await expect(save).toBeEnabled();
    await save.focus();
    await expect(save).toBeFocused();
    await save.press('Enter');
    await expect(page.getByText('All changes are saved.')).toBeVisible();

    const back = page.getByRole('button', { name: 'Back' });
    await back.focus();
    await expect(back).toBeFocused();
    await back.press('Enter');
    await expect(page).toHaveURL(/\/$/);
  });

  test('admin navigation and responsive row controls operate from the keyboard', async ({
    context,
    page,
  }, testInfo) => {
    // Intentional project gate: this set covers each responsive admin-table mode once.
    test.skip(!adminProjects.has(testInfo.project.name), 'One project per responsive table mode');
    await authenticate(context);
    await page.goto('/admin/jobs');
    await expect(page.getByRole('heading', { name: 'Jobs', exact: true })).toBeVisible();

    const navigation = page.locator('nav[aria-label="Admin navigation"]:visible');
    const jobsLink = navigation.getByRole('link', { name: 'Jobs', exact: true });
    await expect(jobsLink).toHaveAttribute('aria-current', 'page');

    const usersLink = navigation.getByRole('link', { name: 'Users', exact: true });
    await usersLink.focus();
    await expect(usersLink).toBeFocused();
    await usersLink.press('Enter');
    await expect(page).toHaveURL(/\/admin\/users$/);
    await page.goto('/admin/jobs');
    await expect(page.getByRole('heading', { name: 'Jobs', exact: true })).toBeVisible();

    if (testInfo.project.name === 'tablet-portrait-chromium') {
      // Use a stable structural locator because the accessible name changes after expansion.
      const details = page.locator('tbody tr').first().locator('button[aria-expanded]');
      await details.focus();
      await expect(details).toBeFocused();
      await details.press('Enter');
      await expect(details).toHaveAttribute('aria-expanded', 'true');
      await expect(page.getByText('Denver, CO')).toBeVisible();
      return;
    }

    const selectRow = page.getByRole('checkbox', { name: 'Select row' }).first();
    await selectRow.focus();
    await expect(selectRow).toBeFocused();
    await selectRow.press('Space');
    await expect(selectRow).toBeChecked();

    const viewJob = page.getByRole('button', { name: 'View job' }).first();
    await viewJob.focus();
    await expect(viewJob).toBeFocused();
    await viewJob.press('Enter');
    await expect(page).toHaveURL(/\/admin\/jobs\/job-frontend-1$/);
  });
});
