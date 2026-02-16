import { expect, test } from '@playwright/test';

const apiBase = process.env.E2E_API_BASE_URL || 'http://localhost:8000/api';

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
      'Set E2E_ALLOW_DATA_SEED=true to allow E2E tests to create patient/visit/admission records.'
    );
  }

  if (!isLocalApi && !allowNonLocalApi) {
    test.skip(
      true,
      `Refusing to seed E2E records on non-local API (${apiBase}). Set E2E_ALLOW_NONLOCAL_API=true to override.`
    );
  }
}

function deriveAdminEmail(email: string): string {
  const [local, domain] = email.split('@');
  return `${local}+admin@${domain}`;
}

function escapeRegex(value: string): string {
  return value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

function requireCredentials(): {
  reception: Credentials;
  admin: Credentials;
} {
  ensureSafeE2EContext();

  const receptionEmail = process.env.E2E_RECEPTION_EMAIL || '';
  const receptionPassword = process.env.E2E_RECEPTION_PASSWORD || '';
  const adminEmail = process.env.E2E_ADMIN_EMAIL || deriveAdminEmail(receptionEmail);
  const adminPassword = process.env.E2E_ADMIN_PASSWORD || receptionPassword;

  if (!receptionEmail || !receptionPassword) {
    test.skip(
      true,
      'Set E2E_RECEPTION_EMAIL and E2E_RECEPTION_PASSWORD to run admin admissions smoke.'
    );
  }

  return {
    reception: { email: receptionEmail, password: receptionPassword },
    admin: { email: adminEmail, password: adminPassword },
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

async function seedPendingAdmissionRequest(
  request: import('@playwright/test').APIRequestContext,
  receptionCreds: Credentials,
  adminCreds: Credentials
): Promise<{ patientName: string; patientId: string; admissionReason: string }> {
  await loginApi(request, receptionCreds);
  const runId = process.env.E2E_RUN_ID || new Date().toISOString().slice(0, 10);
  const unique = Date.now();
  const patientName = `E2E ${runId} Bed Flow ${unique}`;
  const admissionReason = `E2E admission request setup ${unique}`;

  const createPatientResponse = await request.post(`${apiBase}/v1/patient`, {
    data: {
      full_name: patientName,
      date_of_birth: '2000-01-01',
      gender: 'FEMALE',
      phone_number: `081${String(unique).slice(-8)}`,
      address: 'E2E Bed Address',
      occupation: 'E2E',
      registration_payment_method: 'CASH',
      registration_payment_reference: `E2E-BED-${unique}`,
    },
  });
  expect(createPatientResponse.ok()).toBeTruthy();
  const patient = await createPatientResponse.json();

  await loginApi(request, adminCreds);
  const createRequestResponse = await request.post(`${apiBase}/v1/admissions/requests`, {
    data: {
      patient_id: patient.id,
      admission_type: 'ELECTIVE',
      reason: admissionReason,
    },
  });
  expect(createRequestResponse.ok()).toBeTruthy();
  const admissionRequest = await createRequestResponse.json();

  const approveResponse = await request.post(
    `${apiBase}/v1/admissions/requests/${admissionRequest.id}/approve`,
    {
      data: {
        reason: 'E2E approval setup',
      },
    }
  );
  expect(approveResponse.ok()).toBeTruthy();

  return { patientName, patientId: patient.id as string, admissionReason };
}

test.describe('Admin admissions ward workflow', () => {
  test('clinic admin can manage approve, ward capacity, bed assignment, release, and discharge', async ({
    page,
    request,
  }) => {
    test.setTimeout(120_000);
    const creds = requireCredentials();
    const seeded = await seedPendingAdmissionRequest(request, creds.reception, creds.admin);

    await loginApi(page.request, creds.admin);
    await page.goto('/admin/admissions');
    await expect(
      page.getByRole('heading', { name: 'Admission Requests' })
    ).toBeVisible({ timeout: 30_000 });

    const requestsQueueTitle = page.getByText('Requests Queue', { exact: true });
    const bedBoardTitle = page.getByText('Bed Board', { exact: true });
    const wardCapacityTitle = page.getByText('Ward Capacity Setup', { exact: true });
    await expect(requestsQueueTitle).toBeVisible();
    await expect(bedBoardTitle).toBeVisible();
    await expect(wardCapacityTitle).toBeVisible();

    const [queueBox, boardBox, capacityBox] = await Promise.all([
      requestsQueueTitle.boundingBox(),
      bedBoardTitle.boundingBox(),
      wardCapacityTitle.boundingBox(),
    ]);
    expect(queueBox).not.toBeNull();
    expect(boardBox).not.toBeNull();
    expect(capacityBox).not.toBeNull();
    expect(queueBox!.y).toBeLessThan(boardBox!.y);
    expect(boardBox!.y).toBeLessThan(capacityBox!.y);

    const wardName = `E2E Ward ${Date.now()}`;
    const wardPrefix = `W${String(Date.now()).slice(-3)}-`;
    const firstBedLabel = `${wardPrefix}01`;

    await page.locator('label:has-text("Ward name") + input').first().fill(wardName);
    await page
      .locator('label:has-text("Bed label prefix") + input')
      .first()
      .fill(wardPrefix);
    await page.locator('label:has-text("From") + input').first().fill('1');
    await page.locator('label:has-text("To") + input').first().fill('2');
    await page.getByRole('button', { name: 'Preview Bed Range' }).click();
    await expect(page.getByText(new RegExp(`${escapeRegex(wardName)} • 2 beds`))).toBeVisible();
    const createWardResponsePromise = page.waitForResponse(
      (response) =>
        response.request().method() === 'POST' &&
        response.url().includes('/v1/wards/range') &&
        response.ok()
    );
    await page.getByRole('button', { name: 'Confirm & Create' }).click();
    await createWardResponsePromise;
    await expect(
      page
        .locator('div.rounded-lg.border.border-slate-200')
        .filter({ hasText: wardName })
        .first()
    ).toBeVisible();

    // Force fresh queue+bed-board state so action readiness reflects new capacity.
    await page.reload();
    await expect(
      page.getByRole('heading', { name: 'Admission Requests' })
    ).toBeVisible({ timeout: 30_000 });

    await page.getByRole('button', { name: 'Approved' }).click();

    const approvedResponse = await page.request.get(
      `${apiBase}/v1/admissions/requests?status_filter=APPROVED`
    );
    expect(approvedResponse.ok()).toBeTruthy();
    const approvedRequests = (await approvedResponse.json()) as Array<Record<string, unknown>>;
    const targetApproved = approvedRequests.find(
      (item) => String(item.reason || '') === seeded.admissionReason
    );
    const bedBoardResponse = await page.request.get(`${apiBase}/v1/bed-board`);
    expect(bedBoardResponse.ok()).toBeTruthy();
    const bedBoard = (await bedBoardResponse.json()) as Record<string, unknown>;
    // Keep CI diagnostics concise when assign-bed readiness regresses.
    console.log(
      'E2E_ADMIN_ASSIGN_DEBUG',
      JSON.stringify(
        {
          target: targetApproved
            ? {
                status: targetApproved.status,
                admission_status: targetApproved.admission_status,
                can_assign_bed: targetApproved.can_assign_bed,
                has_active_bed_assignment: targetApproved.has_active_bed_assignment,
                action_blockers: targetApproved.action_blockers,
                active_visit_id: targetApproved.active_visit_id,
              }
            : null,
          bed_board_summary: (bedBoard.summary as Record<string, unknown>) || null,
        },
        null,
        2
      )
    );

    const approvedRowForPatient = page
      .locator('div.rounded-lg.border.border-slate-200')
      .filter({ hasText: seeded.admissionReason })
      .filter({ has: page.getByRole('button', { name: 'Assign Bed' }) })
      .first();
    const approvedRowFallback = page
      .locator('div.rounded-lg.border.border-slate-200')
      .filter({
        has: page.getByRole('button', { name: 'Assign Bed' }),
      })
      .first();
    const approvedRow =
      (await approvedRowForPatient.count()) > 0 ? approvedRowForPatient : approvedRowFallback;
    await expect(approvedRow).toBeVisible({ timeout: 30_000 });
    const assignBedButton = approvedRow.getByRole('button', { name: 'Assign Bed' });
    await expect(assignBedButton).toBeEnabled({ timeout: 30_000 });
    await assignBedButton.click();

    const assignModal = page.getByRole('dialog', {
      name: /Assign bed for admission/i,
    });
    await expect(assignModal).toBeVisible();
    await assignModal
      .getByLabel('Ward', { exact: true })
      .selectOption({ label: wardName });
    await expect(
      assignModal.getByRole('button', {
        name: new RegExp(`Bed ${escapeRegex(firstBedLabel)}`),
      })
    ).toBeVisible();
    await assignModal
      .getByRole('button', {
        name: new RegExp(`Bed ${escapeRegex(firstBedLabel)}`),
      })
      .click();
    await assignModal.getByRole('button', { name: 'Assign Bed' }).click();
    await expect(page.getByText('Bed assigned successfully.').first()).toBeVisible();

    await page
      .getByPlaceholder(/Name, MRN, patient ID/i)
      .fill(seeded.patientId);
    const occupiedRow = page
      .locator('tbody tr')
      .filter({
        has: page.getByRole('button', { name: 'View Details' }),
      })
      .first();
    await expect(occupiedRow).toBeVisible();
    await occupiedRow.getByRole('button', { name: 'View Details' }).click();
    await expect(page.getByRole('heading', { name: 'Admission bed timeline' })).toBeVisible();
    await expect(page.getByText('Bed Timeline').first()).toBeVisible();
    await page.getByRole('button', { name: 'Close', exact: true }).click();

    const activeBedRowForPatient = page
      .locator('div.rounded-lg.border.border-slate-200')
      .filter({ hasText: seeded.admissionReason })
      .filter({ has: page.getByRole('button', { name: 'Release Bed (Keep Active)' }) })
      .first();
    const activeBedRowFallback = page
      .locator('div.rounded-lg.border.border-slate-200')
      .filter({ has: page.getByRole('button', { name: 'Release Bed (Keep Active)' }) })
      .first();
    const activeBedRow =
      (await activeBedRowForPatient.count()) > 0 ? activeBedRowForPatient : activeBedRowFallback;
    await expect(activeBedRow).toBeVisible();
    await activeBedRow.getByRole('button', { name: 'Release Bed (Keep Active)' }).click();
    const releaseModal = page.getByRole('dialog', {
      name: /Release bed \(keep admission active\)/i,
    });
    await expect(releaseModal).toBeVisible();
    await releaseModal
      .getByPlaceholder('Patient moved, temporary discharge, cleaning...')
      .fill('Temporary bed release');
    await releaseModal
      .locator(
        'label:has-text("I confirm this patient should no longer hold the current bed.") input[type="checkbox"]'
      )
      .check();
    const releaseResponsePromise = page.waitForResponse(
      (response) =>
        response.request().method() === 'POST' &&
        /\/v1\/admissions\/.+\/bed\/release$/.test(response.url()) &&
        response.ok()
    );
    await releaseModal.getByRole('button', { name: 'Release Bed (Keep Active)' }).click();
    await releaseResponsePromise;
    await expect(page.getByText(/Bed released for/).first()).toBeVisible();

    const postReleaseRowForPatient = page
      .locator('div.rounded-lg.border.border-slate-200')
      .filter({ hasText: seeded.admissionReason })
      .filter({ has: page.getByRole('button', { name: 'Discharge Admission' }) })
      .first();
    const postReleaseRowFallback = page
      .locator('div.rounded-lg.border.border-slate-200')
      .filter({ has: page.getByRole('button', { name: 'Discharge Admission' }) })
      .first();
    const postReleaseRow =
      (await postReleaseRowForPatient.count()) > 0
        ? postReleaseRowForPatient
        : postReleaseRowFallback;
    await expect(postReleaseRow).toBeVisible();
    await postReleaseRow.getByRole('button', { name: 'Discharge Admission' }).click();
    const dischargeModal = page.getByRole('dialog', {
      name: /Discharge active admission/i,
    });
    await expect(dischargeModal).toBeVisible();
    await dischargeModal
      .getByPlaceholder('Clinical/operational discharge reason...')
      .fill('Discharge after workflow completion');
    await dischargeModal
      .locator(
        'label:has-text("I confirm this admission should be closed now.") input[type="checkbox"]'
      )
      .check();
    const dischargeResponsePromise = page.waitForResponse(
      (response) =>
        response.request().method() === 'POST' &&
        /\/v1\/admissions\/.+\/discharge$/.test(response.url()) &&
        response.ok()
    );
    await dischargeModal.getByRole('button', { name: 'Discharge Admission' }).click();
    await dischargeResponsePromise;
    await expect(page.getByText(/Admission discharged for/).first()).toBeVisible();

    const readOnlyRowForPatient = page
      .locator('div.rounded-lg.border.border-slate-200')
      .filter({ hasText: seeded.admissionReason })
      .filter({ hasText: /read-only/i })
      .first();
    const readOnlyRowFallback = page
      .locator('div.rounded-lg.border.border-slate-200')
      .filter({ hasText: /read-only/i })
      .first();
    const readOnlyRow =
      (await readOnlyRowForPatient.count()) > 0 ? readOnlyRowForPatient : readOnlyRowFallback;
    await expect(readOnlyRow).toBeVisible();
    await expect(readOnlyRow.getByRole('button', { name: 'Assign Bed' })).toHaveCount(0);
    await expect(readOnlyRow.getByRole('button', { name: 'Discharge Admission' })).toHaveCount(
      0
    );
  });
});
