import { expect, test } from '@playwright/test';

const apiBase = process.env.E2E_API_BASE_URL || 'http://localhost:8110/api';

function requireAccountantCredentials(): { email: string; password: string } {
  const email = process.env.E2E_ACCOUNTANT_EMAIL || '';
  const password = process.env.E2E_ACCOUNTANT_PASSWORD || '';
  if (!email || !password) {
    test.skip(
      true,
      'Set E2E_ACCOUNTANT_EMAIL and E2E_ACCOUNTANT_PASSWORD to run accountant dashboard workspace tests.'
    );
  }
  return { email, password };
}

async function loginApi(
  request: import('@playwright/test').APIRequestContext,
  creds: { email: string; password: string }
) {
  const response = await request.post(`${apiBase}/v1/auth/login`, {
    data: creds,
  });
  expect(response.ok()).toBeTruthy();
}

test.describe('Accountant dashboard workspace', () => {
  const creds = requireAccountantCredentials();

  test('loads enterprise accountant sections without runtime failures', async ({ page }) => {
    const runtimeFailures: string[] = [];
    const serverFailures: string[] = [];

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

    await loginApi(page.request, creds);
    await page.goto('/accountant', { waitUntil: 'networkidle' });

    await expect(page.getByRole('heading', { name: 'Accountant Dashboard' })).toBeVisible({
      timeout: 30_000,
    });
    await expect(page.getByRole('heading', { name: 'Filters' })).toBeVisible();
    await expect(page.getByText('Revenue Today')).toBeVisible();
    await expect(page.getByText('Revenue This Month')).toBeVisible();
    await expect(page.getByText('Cashier Session Oversight')).toBeVisible();
    await expect(page.getByText('Refund Monitoring')).toBeVisible();
    await expect(page.getByText('Audit Activity Feed')).toBeVisible();
    await expect(page.getByText('Fraud Prevention Signals')).toBeVisible();

    expect(runtimeFailures, 'Runtime failures on accountant dashboard').toEqual([]);
    expect(serverFailures, 'Server failures from accountant dashboard API calls').toEqual(
      []
    );
  });
});

