import { expect, test, type Page } from '@playwright/test';

const apiBase = process.env.E2E_API_BASE_URL || 'http://localhost:8000/api';
const followUpFixturePatientName = 'E2E Follow-Up Linked Visit';
const doctorFixturePatientName = 'E2E Doctor Queue Action';
const labFixturePatientName = 'E2E Lab Queue Action';
const pharmacyFixturePatientName = 'E2E Pharmacy Queue Action';

type Credentials = { email: string; password: string };

function ensureSafeE2EContext(): void {
  const allowSeed = process.env.E2E_ALLOW_DATA_SEED === 'true';
  const allowNonLocalApi = process.env.E2E_ALLOW_NONLOCAL_API === 'true';
  const isLocalApi =
    apiBase.startsWith('http://localhost:') ||
    apiBase.startsWith('http://127.0.0.1:');

  if (!allowSeed) {
    test.skip(
      true,
      'Set E2E_ALLOW_DATA_SEED=true to allow E2E tests to create patient/visit records.'
    );
  }

  if (!isLocalApi && !allowNonLocalApi) {
    test.skip(
      true,
      `Refusing to seed E2E records on non-local API (${apiBase}). Set E2E_ALLOW_NONLOCAL_API=true to override.`
    );
  }
}

function deriveRoleEmail(email: string, suffix: string): string {
  const [local, domain] = email.split('@');
  return `${local}+${suffix}@${domain}`;
}

function requireCredentials(): {
  reception: Credentials;
  chew: Credentials;
  doctor: Credentials;
  lab: Credentials;
  pharmacy: Credentials;
} {
  ensureSafeE2EContext();

  const receptionEmail = process.env.E2E_RECEPTION_EMAIL || '';
  const receptionPassword = process.env.E2E_RECEPTION_PASSWORD || '';
  const chewEmail = process.env.E2E_CHEW_EMAIL || '';
  const chewPassword = process.env.E2E_CHEW_PASSWORD || '';
  const doctorEmail =
    process.env.E2E_DOCTOR_EMAIL || deriveRoleEmail(receptionEmail, 'doctor');
  const doctorPassword = process.env.E2E_DOCTOR_PASSWORD || receptionPassword;
  const labEmail = process.env.E2E_LAB_EMAIL || deriveRoleEmail(receptionEmail, 'lab');
  const labPassword = process.env.E2E_LAB_PASSWORD || receptionPassword;
  const pharmacyEmail =
    process.env.E2E_PHARMACY_EMAIL || deriveRoleEmail(receptionEmail, 'pharmacy');
  const pharmacyPassword = process.env.E2E_PHARMACY_PASSWORD || receptionPassword;

  if (!receptionEmail || !receptionPassword || !chewEmail || !chewPassword) {
    test.skip(
      true,
      'Set E2E_RECEPTION_* and E2E_CHEW_* credentials to run role action smoke.'
    );
  }

  return {
    reception: { email: receptionEmail, password: receptionPassword },
    chew: { email: chewEmail, password: chewPassword },
    doctor: { email: doctorEmail, password: doctorPassword },
    lab: { email: labEmail, password: labPassword },
    pharmacy: { email: pharmacyEmail, password: pharmacyPassword },
  };
}

function startFailureTracking(page: Page): {
  serverFailures: string[];
  runtimeFailures: string[];
} {
  const serverFailures: string[] = [];
  const runtimeFailures: string[] = [];
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
  page.on('pageerror', (error) => {
    runtimeFailures.push(error.message);
  });
  return { serverFailures, runtimeFailures };
}

function assertNoFailures(
  label: string,
  failures: { serverFailures: string[]; runtimeFailures: string[] }
): void {
  expect(failures.serverFailures, `Server failures seen for ${label}`).toEqual([]);
  expect(failures.runtimeFailures, `Runtime failures seen for ${label}`).toEqual([]);
}

async function loginApi(
  request: import('@playwright/test').APIRequestContext,
  creds: Credentials
) {
  const response = await request.post(`${apiBase}/v1/auth/login`, {
    data: creds,
  });
  expect(response.ok()).toBeTruthy();
}

test.describe('Role dashboard action smoke', () => {
  test('Reception starts linked follow-up visit from dashboard', async ({ page }) => {
    const creds = requireCredentials();
    const failures = startFailureTracking(page);

    await loginApi(page.request, creds.reception);
    await page.goto('/reception', { waitUntil: 'networkidle' });
    await expect(
      page.getByRole('heading', { name: /Reception Dashboard/i })
    ).toBeVisible();

    const followUpRow = page
      .locator('div')
      .filter({ hasText: followUpFixturePatientName })
      .filter({ has: page.getByRole('button', { name: 'Start Visit (Link)' }) })
      .first();
    await expect(followUpRow).toBeVisible({ timeout: 30_000 });
    await followUpRow.getByRole('button', { name: 'Start Visit (Link)' }).click();

    await expect(
      page.getByText(/Linked visit started|Active visit already exists/i).first()
    ).toBeVisible({ timeout: 20_000 });

    assertNoFailures('RECEPTION action smoke', failures);
  });

  test('Doctor opens queue item details', async ({ page }) => {
    const creds = requireCredentials();
    const failures = startFailureTracking(page);

    await loginApi(page.request, creds.doctor);
    await page.goto('/doctor', { waitUntil: 'networkidle' });
    await expect(page.getByRole('heading', { name: /Doctor Dashboard/i })).toBeVisible();

    const row = page
      .locator('div')
      .filter({ hasText: doctorFixturePatientName })
      .filter({ has: page.getByRole('button', { name: 'View Details' }) })
      .first();
    await expect(row).toBeVisible({ timeout: 30_000 });
    await row.getByRole('button', { name: 'View Details' }).click();

    await expect(page.getByRole('heading', { name: 'Visit Details' })).toBeVisible();

    assertNoFailures('DOCTOR action smoke', failures);
  });

  test('Lab opens pending request modal', async ({ page }) => {
    const creds = requireCredentials();
    const failures = startFailureTracking(page);

    await loginApi(page.request, creds.lab);
    await page.goto('/lab', { waitUntil: 'networkidle' });
    await expect(page.getByRole('heading', { name: /Lab Dashboard/i })).toBeVisible();

    const row = page
      .locator('div')
      .filter({ hasText: labFixturePatientName })
      .filter({ has: page.getByRole('button', { name: 'Process' }) })
      .first();
    await expect(row).toBeVisible({ timeout: 30_000 });
    await row.getByRole('button', { name: 'Process' }).click();

    await expect(page.getByRole('heading', { name: /Lab Request:/i })).toBeVisible();

    assertNoFailures('LAB action smoke', failures);
  });

  test('Pharmacy opens dispense modal from queue item', async ({ page }) => {
    const creds = requireCredentials();
    const failures = startFailureTracking(page);

    await loginApi(page.request, creds.pharmacy);
    await page.goto('/pharmacy', { waitUntil: 'networkidle' });
    await expect(
      page.getByRole('heading', { name: /Pharmacy Dashboard/i })
    ).toBeVisible();

    const row = page
      .locator('div')
      .filter({ hasText: pharmacyFixturePatientName })
      .filter({ has: page.getByRole('button', { name: 'Dispense' }) })
      .first();
    await expect(row).toBeVisible({ timeout: 30_000 });
    await row.getByRole('button', { name: 'Dispense' }).click();

    await expect(
      page.getByRole('heading', { name: /Dispense Medication/i })
    ).toBeVisible();

    assertNoFailures('PHARMACY action smoke', failures);
  });
});
