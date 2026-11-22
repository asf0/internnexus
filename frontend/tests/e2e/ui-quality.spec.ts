import { expect, test } from '@playwright/test';
import {
  authenticate,
  expectNoDocumentOverflow,
  expectNoSeriousAccessibilityViolations,
  preparePage,
} from './support/quality';

test.describe('representative UI quality gates', () => {
  test.beforeEach(async ({ page }) => preparePage(page));

  test('public job listings are readable and contained', async ({ page }, testInfo) => {
    await page.goto('/');

    await expect(page.getByRole('heading', { name: 'InternNexus' })).toBeVisible();
    await expect(page.getByRole('article', { name: /Frontend Engineering Intern/ })).toBeVisible();
    await page.getByRole('link', { name: 'Frontend Engineering Intern' }).click();
    await expect(
      page
        .getByText('Build accessible interfaces with a product engineering team.')
        .filter({ visible: true })
    ).toBeVisible();
    await expectNoDocumentOverflow(page);
    await expectNoSeriousAccessibilityViolations(page, testInfo);
  });

  test('account settings remain accessible and contained', async ({ context, page }, testInfo) => {
    await authenticate(context);
    await page.goto('/settings');

    await expect(page.getByRole('heading', { name: 'Account Settings' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Save All Changes' })).toBeVisible();
    await expectNoDocumentOverflow(page);
    await expectNoSeriousAccessibilityViolations(page, testInfo);
  });

  test('admin jobs adapt without document overflow', async ({ context, page }, testInfo) => {
    await authenticate(context);
    await page.goto('/admin/jobs');

    await expect(page.getByRole('heading', { name: 'Jobs', exact: true })).toBeVisible();
    await expect(
      page.getByRole('link', { name: 'Frontend Engineering Intern' }).first()
    ).toBeVisible();
    await expect(page.getByRole('button', { name: 'Create Job' })).toBeVisible();
    await expectNoDocumentOverflow(page);
    await expectNoSeriousAccessibilityViolations(page, testInfo);
  });
});
