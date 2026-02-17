import { expect, test, type Page } from '@playwright/test';

const apiBase = process.env.E2E_API_BASE_URL || 'http://localhost:8000/api';
const followUpFixturePatientName = 'E2E Follow-Up Linked Visit';

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

async function getCurrentUser(
  request: import('@playwright/test').APIRequestContext
): Promise<{ id: string; clinic_id: string; role: string }> {
  const response = await request.get(`${apiBase}/v1/auth/me`);
  expect(response.ok()).toBeTruthy();
  return response.json();
}

function uniqueSuffix(): string {
  return `${Date.now()}${Math.floor(Math.random() * 1000)}`;
}

function idempotencyKey(prefix: string): string {
  return `${prefix}-${uniqueSuffix()}`;
}

async function seedInConsultationVisitForDoctor(
  request: import('@playwright/test').APIRequestContext,
  creds: {
    reception: Credentials;
    chew: Credentials;
    doctor: Credentials;
  },
  label: string
): Promise<{ patientName: string; visitId: string }> {
  await loginApi(request, creds.doctor);
  const doctorUser = await getCurrentUser(request);

  await loginApi(request, creds.reception);
  const unique = uniqueSuffix();
  const patientName = `E2E ${label} ${unique}`;
  const createPatientResponse = await request.post(`${apiBase}/v1/patient`, {
    data: {
      full_name: patientName,
      date_of_birth: '2000-01-01',
      gender: 'FEMALE',
      phone_number: `082${unique.slice(-8)}`,
      address: 'E2E Role Action Fixture',
      occupation: 'E2E',
      registration_payment_method: 'CASH',
      registration_payment_reference: `E2E-ROLE-${unique}`,
    },
  });
  expect(createPatientResponse.ok()).toBeTruthy();
  const patient = (await createPatientResponse.json()) as { id: string };

  const startVisitResponse = await request.post(`${apiBase}/v1/visits/start`, {
    data: {
      patient_id: patient.id,
      assigned_doctor_id: doctorUser.id,
      service_line: 'OPD',
    },
  });
  expect(startVisitResponse.ok()).toBeTruthy();
  const visit = (await startVisitResponse.json()) as { id: string; version: number };

  await loginApi(request, creds.chew);
  const finalizeTriageResponse = await request.post(
    `${apiBase}/v1/visits/${visit.id}/triage/finalize`,
    {
      headers: {
        'Idempotency-Key': idempotencyKey('e2e-triage-finalize'),
      },
      data: {
        expected_version: visit.version,
        action: 'QUEUE_FOR_CONSULTATION',
        acuity_level: 'ROUTINE',
        chief_complaint: 'E2E triage complaint',
        complaint_severity: 'MILD',
        triage_note: 'E2E triage finalize',
        danger_sign_codes: [],
        temp_c: 36.7,
        pulse_bpm: 80,
        rr_bpm: 16,
        sbp_mmhg: 112,
        dbp_mmhg: 72,
        spo2_pct: 98,
        is_doctor_fallback: false,
      },
    }
  );
  expect(finalizeTriageResponse.ok()).toBeTruthy();
  const triagePayload = (await finalizeTriageResponse.json()) as { visit_version: number };

  await loginApi(request, creds.doctor);
  const transitionResponse = await request.post(
    `${apiBase}/v1/visits/${visit.id}/transition`,
    {
      headers: {
        'Idempotency-Key': idempotencyKey('e2e-visit-transition'),
      },
      data: {
        to_status: 'IN_CONSULTATION',
        expected_version: triagePayload.visit_version,
      },
    }
  );
  expect(transitionResponse.ok()).toBeTruthy();

  return { patientName, visitId: visit.id };
}

async function seedLabAndPharmacyWorkItem(
  request: import('@playwright/test').APIRequestContext,
  creds: {
    reception: Credentials;
    chew: Credentials;
    doctor: Credentials;
  }
): Promise<{ patientName: string }> {
  const visitFixture = await seedInConsultationVisitForDoctor(
    request,
    creds,
    'LabPharmacy'
  );

  await loginApi(request, creds.doctor);
  const startConsultationResponse = await request.post(
    `${apiBase}/v1/consultations/start`,
    {
      data: { visit_id: visitFixture.visitId },
    }
  );
  expect(startConsultationResponse.ok()).toBeTruthy();
  const consultation = (await startConsultationResponse.json()) as { id: string };

  const createLabRequestResponse = await request.post(`${apiBase}/v1/lab/requests`, {
    data: {
      visit_id: visitFixture.visitId,
      test_name: 'Full Blood Count (E2E)',
      special_instructions: 'Role action smoke fixture',
    },
  });
  expect(createLabRequestResponse.ok()).toBeTruthy();

  const createPrescriptionResponse = await request.post(`${apiBase}/v1/prescriptions`, {
    data: {
      consultation_id: consultation.id,
      drug_name: 'Paracetamol 500mg',
      dosage: '1 tablet',
      frequency: 'TDS',
      duration: '3 days',
      instructions: 'After meals',
    },
  });
  expect(createPrescriptionResponse.ok()).toBeTruthy();

  return { patientName: visitFixture.patientName };
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

  test('Doctor opens queue item details', async ({ page, request }) => {
    test.setTimeout(120_000);
    const creds = requireCredentials();
    const seeded = await seedInConsultationVisitForDoctor(
      request,
      {
        reception: creds.reception,
        chew: creds.chew,
        doctor: creds.doctor,
      },
      'DoctorAction'
    );
    const failures = startFailureTracking(page);

    await loginApi(page.request, creds.doctor);
    await page.goto('/doctor', { waitUntil: 'networkidle' });
    await expect(page.getByRole('heading', { name: /Doctor Dashboard/i })).toBeVisible();

    const row = page
      .locator('div')
      .filter({ hasText: seeded.patientName })
      .filter({ has: page.getByRole('button', { name: 'View Details' }) })
      .first();
    await expect(row).toBeVisible({ timeout: 30_000 });
    await row.getByRole('button', { name: 'View Details' }).click();

    await expect(page.getByRole('heading', { name: 'Visit Details' })).toBeVisible();

    assertNoFailures('DOCTOR action smoke', failures);
  });

  test('Lab opens pending request modal', async ({ page, request }) => {
    test.setTimeout(120_000);
    const creds = requireCredentials();
    const seeded = await seedLabAndPharmacyWorkItem(request, {
      reception: creds.reception,
      chew: creds.chew,
      doctor: creds.doctor,
    });
    const failures = startFailureTracking(page);

    await loginApi(page.request, creds.lab);
    await page.goto('/lab', { waitUntil: 'networkidle' });
    await expect(page.getByRole('heading', { name: /Lab Dashboard/i })).toBeVisible();

    const row = page
      .locator('div')
      .filter({ hasText: seeded.patientName })
      .filter({ has: page.getByRole('button', { name: 'Process' }) })
      .first();
    await expect(row).toBeVisible({ timeout: 30_000 });
    await row.getByRole('button', { name: 'Process' }).click();

    await expect(page.getByRole('heading', { name: /Lab Request:/i })).toBeVisible();

    assertNoFailures('LAB action smoke', failures);
  });

  test('Pharmacy opens dispense modal from queue item', async ({ page, request }) => {
    test.setTimeout(120_000);
    const creds = requireCredentials();
    const seeded = await seedLabAndPharmacyWorkItem(request, {
      reception: creds.reception,
      chew: creds.chew,
      doctor: creds.doctor,
    });
    const failures = startFailureTracking(page);

    await loginApi(page.request, creds.pharmacy);
    await page.goto('/pharmacy', { waitUntil: 'networkidle' });
    await expect(
      page.getByRole('heading', { name: /Pharmacy Dashboard/i })
    ).toBeVisible();

    const row = page
      .locator('div')
      .filter({ hasText: seeded.patientName })
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
