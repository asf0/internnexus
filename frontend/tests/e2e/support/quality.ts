import AxeBuilder from '@axe-core/playwright';
import { encode } from 'next-auth/jwt';
import type { BrowserContext, Page, TestInfo } from '@playwright/test';
import { expect } from '@playwright/test';

const authSecret = 'browser-test-auth-secret-that-is-at-least-32-characters';
const authCookieName = 'authjs.session-token';

export async function authenticate(context: BrowserContext): Promise<void> {
  const token = await encode({
    secret: authSecret,
    salt: authCookieName,
    maxAge: 60 * 60,
    token: {
      sub: 'user-browser-test',
      id: 'user-browser-test',
      name: 'Alex Rivera',
      email: 'alex@example.test',
      backendToken: 'browser-test-backend-token',
    },
  });

  await context.addCookies([
    {
      name: authCookieName,
      value: token,
      url: 'http://127.0.0.1:3100',
      httpOnly: true,
      sameSite: 'Lax',
    },
  ]);
}

export async function preparePage(page: Page): Promise<void> {
  await page.route(/^https?:\/\/(?!127\.0\.0\.1(?::\d+)?\/).*/, (route) => route.abort());
}

export async function expectNoDocumentOverflow(page: Page): Promise<void> {
  const dimensions = await page.evaluate(() => ({
    viewport: document.documentElement.clientWidth,
    document: document.documentElement.scrollWidth,
    body: document.body.scrollWidth,
  }));
  expect(
    Math.max(dimensions.document, dimensions.body),
    `document width ${Math.max(dimensions.document, dimensions.body)}px exceeds ${dimensions.viewport}px viewport`
  ).toBeLessThanOrEqual(dimensions.viewport);
}

export async function expectNoSeriousAccessibilityViolations(
  page: Page,
  testInfo: TestInfo
): Promise<void> {
  const results = await new AxeBuilder({ page })
    .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
    .analyze();
  const violations = results.violations.filter(
    ({ impact }) => impact === 'serious' || impact === 'critical'
  );

  if (violations.length > 0) {
    await testInfo.attach('axe-violations', {
      body: JSON.stringify(violations, null, 2),
      contentType: 'application/json',
    });
  }
  expect(violations, 'serious or critical Axe violations').toEqual([]);
}
