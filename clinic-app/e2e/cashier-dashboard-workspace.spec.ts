import { expect, test } from '@playwright/test';
import { newLoggedInPage } from './support/auth';

function requireCashierCredentials(): { email: string; password: string } {
  const email = process.env.E2E_CASHIER_EMAIL || '';
  const password = process.env.E2E_CASHIER_PASSWORD || '';
  if (!email || !password) {
    test.skip(
      true,
      'Set E2E_CASHIER_EMAIL and E2E_CASHIER_PASSWORD to run cashier dashboard workspace tests.'
    );
  }
  return { email, password };
}

test.describe('Cashier dashboard workspace', () => {
  const creds = requireCashierCredentials();

  test('loads enterprise cashier layout sections without runtime failures', async ({
    browser,
    playwright,
  }) => {
    const { context, page } = await newLoggedInPage(browser, playwright, creds);
    const runtimeFailures: string[] = [];
    const serverFailures: string[] = [];
    try {
      page.on('pageerror', (error) => runtimeFailures.push(error.message));
      page.on('response', (response) => {
        if (!response.url().includes('/api/')) {
          return;
        }
        if (response.status() >= 500) {
          serverFailures.push(
            `${response.status()} ${response.request().method()} ${response.url()}`
          );
        }
      });

      await page.goto('/cashier', { waitUntil: 'domcontentloaded' });

      await expect(
        page.getByRole('heading', { name: 'Cashier Financial Workstation' })
      ).toBeVisible({ timeout: 30_000 });
      await expect(
        page.getByRole('heading', { name: 'Cashier Navigation' })
      ).toBeVisible();
      await expect(
        page.getByRole('button', { name: /^Pending Charges\b/ })
      ).toBeVisible();
      await expect(
        page.getByRole('heading', { name: 'Pharmacy Charges' })
      ).toBeVisible();
      await expect(page.getByText('Receipts Today', { exact: true })).toBeVisible();
      await expect(page.getByRole('heading', { name: 'Recent Receipts' })).toBeVisible();
      await expect(page.getByRole('heading', { name: 'Activity Audit' })).toBeVisible();

      expect(runtimeFailures, 'Runtime failures on cashier dashboard').toEqual([]);
      expect(serverFailures, 'Server failures from cashier dashboard API calls').toEqual(
        []
      );
    } finally {
      await context.close();
    }
  });

  test('navigates within sidebar sections for receipts and pharmacy charges', async ({
    browser,
    playwright,
  }) => {
    const { context, page } = await newLoggedInPage(browser, playwright, creds);
    try {
      await page.goto('/cashier', { waitUntil: 'domcontentloaded' });

      await page.getByRole('button', { name: 'Receipts' }).click();
      await expect(page.getByRole('heading', { name: 'Receipts' })).toBeVisible();

      await page.getByRole('button', { name: 'Pharmacy Charges' }).click();
      await expect(
        page.getByRole('heading', { name: 'Pharmacy Charges' })
      ).toBeVisible();
      await expect(
        page.getByRole('heading', { name: 'Payment Collection' })
      ).toBeVisible();
    } finally {
      await context.close();
    }
  });

  test('navigates to transactions workspace and shows filters', async ({
    browser,
    playwright,
  }) => {
    const { context, page } = await newLoggedInPage(browser, playwright, creds);
    try {
      await page.goto('/cashier', { waitUntil: 'domcontentloaded' });

      await page.getByRole('link', { name: 'Full Activities' }).click();
      await expect(page).toHaveURL(/\/cashier\/transactions$/);

      await expect(
        page.getByRole('heading', { name: 'Cashier Full Activities' })
      ).toBeVisible();
      await expect(page.getByRole('link', { name: '← Back to Cashier Desk' })).toBeVisible();
      await expect(page.getByRole('button', { name: 'Export CSV' })).toBeVisible();
      await expect(page.getByRole('heading', { name: 'Filters' })).toBeVisible();
      await expect(page.getByLabel('From', { exact: true })).toBeVisible();
      await expect(page.getByLabel('To', { exact: true })).toBeVisible();
      await expect(page.getByRole('combobox')).toBeVisible();
      await expect(page.getByLabel('Search', { exact: true })).toBeVisible();
      await expect(page.getByRole('button', { name: 'Apply Filters' })).toBeVisible();
    } finally {
      await context.close();
    }
  });
});
