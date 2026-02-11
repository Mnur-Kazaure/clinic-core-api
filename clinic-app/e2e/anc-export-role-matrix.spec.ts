import { expect, test } from '@playwright/test';

const apiBase = process.env.E2E_API_BASE_URL || 'http://localhost:8000/api';

type Credentials = { email: string; password: string };

function deriveColleagueEmail(email: string): string {
  const [local, domain] = email.split('@');
  return `${local}+colleague@${domain}`;
}

function requireCredentials(): {
  reception: Credentials;
  chew: Credentials;
  chewColleague: Credentials;
  midwife: Credentials;
} {
  const receptionEmail = process.env.E2E_RECEPTION_EMAIL || '';
  const receptionPassword = process.env.E2E_RECEPTION_PASSWORD || '';
  const chewEmail = process.env.E2E_CHEW_EMAIL || '';
  const chewPassword = process.env.E2E_CHEW_PASSWORD || '';
  const midwifeEmail = process.env.E2E_MIDWIFE_EMAIL || '';
  const midwifePassword = process.env.E2E_MIDWIFE_PASSWORD || '';

  if (
    !receptionEmail ||
    !receptionPassword ||
    !chewEmail ||
    !chewPassword ||
    !midwifeEmail ||
    !midwifePassword
  ) {
    test.skip(
      true,
      'Set E2E_RECEPTION_*, E2E_CHEW_*, and E2E_MIDWIFE_* credentials to run ANC export smoke.'
    );
  }

  return {
    reception: { email: receptionEmail, password: receptionPassword },
    chew: { email: chewEmail, password: chewPassword },
    chewColleague: {
      email: deriveColleagueEmail(chewEmail),
      password: chewPassword,
    },
    midwife: { email: midwifeEmail, password: midwifePassword },
  };
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

async function getCurrentUser(
  request: import('@playwright/test').APIRequestContext
): Promise<{ id: string; role: string; clinic_id: string }> {
  const response = await request.get(`${apiBase}/v1/auth/me`);
  expect(response.ok()).toBeTruthy();
  return response.json();
}

async function seedAncVisitForChew(
  request: import('@playwright/test').APIRequestContext,
  receptionCreds: Credentials,
  chewCreds: Credentials
): Promise<{ episodeId: string; patientName: string }> {
  await loginApi(request, receptionCreds);

  await loginApi(request, chewCreds);
  const chewUser = await getCurrentUser(request);

  await loginApi(request, receptionCreds);
  const unique = Date.now();
  const patientName = `E2E ANC ${unique}`;
  const createPatientResponse = await request.post(`${apiBase}/v1/patient`, {
    data: {
      full_name: patientName,
      date_of_birth: '2000-01-01',
      gender: 'FEMALE',
      phone_number: `080${String(unique).slice(-8)}`,
      address: 'E2E Test Address',
      occupation: 'E2E',
      registration_payment_method: 'CASH',
      registration_payment_reference: `E2E-${unique}`,
    },
  });
  expect(createPatientResponse.ok()).toBeTruthy();
  const patient = await createPatientResponse.json();

  const startVisitResponse = await request.post(`${apiBase}/v1/visits/start`, {
    data: {
      patient_id: patient.id,
      assigned_doctor_id: chewUser.id,
      service_line: 'ANC',
    },
  });
  expect(startVisitResponse.ok()).toBeTruthy();

  await loginApi(request, chewCreds);
  const createEpisodeResponse = await request.post(
    `${apiBase}/v1/anc/patients/${patient.id}/episodes`,
    {
      data: {
        gravida: 1,
        parity: 0,
      },
    }
  );
  expect(createEpisodeResponse.ok()).toBeTruthy();
  const episode = await createEpisodeResponse.json();

  return { episodeId: episode.id, patientName };
}

test.describe('ANC export role matrix', () => {
  test('RECEPTION can export ANC PDF via API', async ({ request }) => {
    const creds = requireCredentials();
    const seeded = await seedAncVisitForChew(request, creds.reception, creds.chew);

    await loginApi(request, creds.reception);
    const exportResponse = await request.get(
      `${apiBase}/v1/anc/episodes/${seeded.episodeId}/export.pdf`,
      {
        params: {
          purpose_of_use: 'OPERATIONS',
          justification: 'Reception ANC export smoke',
        },
      }
    );

    expect(exportResponse.status()).toBe(200);
    expect(exportResponse.headers()['content-type']).toContain('application/pdf');
    const body = await exportResponse.body();
    expect(body.subarray(0, 8).toString()).toContain('%PDF-1.4');
  });

  test('MIDWIFE is denied ANC export via API by default', async ({ request }) => {
    const creds = requireCredentials();
    const seeded = await seedAncVisitForChew(request, creds.reception, creds.chew);

    await loginApi(request, creds.midwife);
    const exportResponse = await request.get(
      `${apiBase}/v1/anc/episodes/${seeded.episodeId}/export.pdf`,
      {
        params: {
          purpose_of_use: 'TREATMENT',
          justification: 'Maternity export attempt',
        },
      }
    );
    expect(exportResponse.status()).toBe(403);
  });

  test('CHEW can export from ANC dashboard modal (UI)', async ({ page, request }) => {
    const creds = requireCredentials();
    const seeded = await seedAncVisitForChew(request, creds.reception, creds.chew);

    await loginApi(page.request, creds.chew);
    await page.goto('/anc');

    await expect(page.getByRole('heading', { name: 'ANC Dashboard' })).toBeVisible();

    await page.getByRole('button', { name: new RegExp(seeded.patientName) }).click();
    await page.getByRole('button', { name: 'Export PDF' }).click();

    await expect(page.getByRole('heading', { name: 'Export ANC PDF' })).toBeVisible();
    await page.locator('textarea').fill('CHEW ANC export smoke');

    const exportResponsePromise = page.waitForResponse((response) => {
      return (
        response.url().includes('/v1/anc/episodes/') &&
        response.url().includes('/export.pdf') &&
        response.status() === 200
      );
    });
    await page.getByRole('button', { name: 'Generate PDF' }).click();
    const exportResponse = await exportResponsePromise;
    const contentType = exportResponse.headers()['content-type'] || '';
    expect(contentType).toContain('application/pdf');
    await expect(page.getByRole('heading', { name: 'Export ANC PDF' })).not.toBeVisible();
  });

  test('CHEW can reassign ANC visit to colleague and colleague sees queue (UI)', async ({
    page,
    request,
  }) => {
    const creds = requireCredentials();
    const seeded = await seedAncVisitForChew(request, creds.reception, creds.chew);

    await loginApi(page.request, creds.chew);
    await page.goto('/anc');
    await expect(page.getByRole('heading', { name: 'ANC Dashboard' })).toBeVisible();

    await page.getByRole('button', { name: new RegExp(seeded.patientName) }).click();
    await page.getByRole('button', { name: 'Reassign Owner' }).click();
    await expect(page.getByRole('heading', { name: 'Reassign ANC Owner' })).toBeVisible();

    await page.locator('select').filter({ hasText: 'Select CHEW' }).selectOption({
      label: 'E2E CHEW Colleague',
    });
    await page.getByRole('button', { name: /^Reassign$/ }).click();

    await expect(
      page.getByRole('button', { name: new RegExp(seeded.patientName) })
    ).not.toBeVisible({ timeout: 15_000 });

    await loginApi(page.request, creds.chewColleague);
    await page.goto('/anc');
    await expect(page.getByRole('heading', { name: 'ANC Dashboard' })).toBeVisible();
    await expect(
      page.getByRole('button', { name: new RegExp(seeded.patientName) })
    ).toBeVisible({ timeout: 15_000 });
  });

  test('CHEW can send ANC visit to maternity and MIDWIFE sees it in queue (UI)', async ({
    page,
    request,
  }) => {
    const creds = requireCredentials();
    const seeded = await seedAncVisitForChew(request, creds.reception, creds.chew);

    await loginApi(page.request, creds.chew);
    await page.goto('/anc');
    await expect(page.getByRole('heading', { name: 'ANC Dashboard' })).toBeVisible();

    await page.getByRole('button', { name: new RegExp(seeded.patientName) }).click();
    await page.getByRole('button', { name: 'Send to Maternity' }).click();
    await expect(
      page.getByRole('heading', { name: 'Send Visit to Maternity' })
    ).toBeVisible();

    await page.locator('select').filter({ hasText: 'Select Midwife' }).selectOption({
      label: 'E2E Midwife',
    });
    await page.getByRole('button', { name: 'Confirm Send' }).click();

    await expect(
      page.getByRole('button', { name: new RegExp(seeded.patientName) })
    ).not.toBeVisible({ timeout: 15_000 });

    await loginApi(page.request, creds.midwife);
    await page.goto('/maternity');
    await expect(
      page.getByRole('heading', { name: 'Maternity Dashboard' })
    ).toBeVisible();
    await expect(
      page.getByRole('button', { name: new RegExp(seeded.patientName) })
    ).toBeVisible({ timeout: 15_000 });
  });
});
