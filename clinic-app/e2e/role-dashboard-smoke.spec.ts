import { expect, test } from '@playwright/test';
import { newLoggedInPage, type E2ECredentials } from './support/auth';

type RoleDashboardCase = {
  label: string;
  path: string;
  heading: RegExp;
  supportHeading?: {
    name: string | RegExp;
    exact?: boolean;
  };
  creds: E2ECredentials;
};

function deriveRoleEmail(email: string, suffix: string): string {
  const [local, domain] = email.split('@');
  return `${local}+${suffix}@${domain}`;
}

function requireCredentials(): {
  reception: E2ECredentials;
  chew: E2ECredentials;
  midwife: E2ECredentials;
  doctor: E2ECredentials;
  lab: E2ECredentials;
  pharmacy: E2ECredentials;
  cmd: E2ECredentials;
  pharmacyHod: E2ECredentials;
  pharmacyStore: E2ECredentials;
} {
  const receptionEmail = process.env.E2E_RECEPTION_EMAIL || '';
  const receptionPassword = process.env.E2E_RECEPTION_PASSWORD || '';
  const chewEmail = process.env.E2E_CHEW_EMAIL || '';
  const chewPassword = process.env.E2E_CHEW_PASSWORD || '';
  const midwifeEmail = process.env.E2E_MIDWIFE_EMAIL || '';
  const midwifePassword = process.env.E2E_MIDWIFE_PASSWORD || '';
  const doctorEmail =
    process.env.E2E_DOCTOR_EMAIL || deriveRoleEmail(receptionEmail, 'doctor');
  const doctorPassword = process.env.E2E_DOCTOR_PASSWORD || receptionPassword;
  const labEmail = process.env.E2E_LAB_EMAIL || deriveRoleEmail(receptionEmail, 'lab');
  const labPassword = process.env.E2E_LAB_PASSWORD || receptionPassword;
  const pharmacyEmail =
    process.env.E2E_PHARMACY_EMAIL || deriveRoleEmail(receptionEmail, 'pharmacy');
  const pharmacyPassword = process.env.E2E_PHARMACY_PASSWORD || receptionPassword;
  const cmdEmail =
    process.env.E2E_CMD_EMAIL || deriveRoleEmail(receptionEmail, 'cmd');
  const cmdPassword = process.env.E2E_CMD_PASSWORD || receptionPassword;
  const pharmacyHodEmail =
    process.env.E2E_PHARMACY_HOD_EMAIL || deriveRoleEmail(receptionEmail, 'pharmacy-hod');
  const pharmacyHodPassword =
    process.env.E2E_PHARMACY_HOD_PASSWORD || receptionPassword;
  const pharmacyStoreEmail =
    process.env.E2E_PHARMACY_STORE_EMAIL || deriveRoleEmail(receptionEmail, 'pharmacy-store');
  const pharmacyStorePassword =
    process.env.E2E_PHARMACY_STORE_PASSWORD || receptionPassword;

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
      'Set E2E_RECEPTION_*, E2E_CHEW_*, and E2E_MIDWIFE_* credentials to run role dashboard smoke.'
    );
  }

  return {
    reception: { email: receptionEmail, password: receptionPassword },
    chew: { email: chewEmail, password: chewPassword },
    midwife: { email: midwifeEmail, password: midwifePassword },
    doctor: { email: doctorEmail, password: doctorPassword },
    lab: { email: labEmail, password: labPassword },
    pharmacy: { email: pharmacyEmail, password: pharmacyPassword },
    cmd: { email: cmdEmail, password: cmdPassword },
    pharmacyHod: { email: pharmacyHodEmail, password: pharmacyHodPassword },
    pharmacyStore: { email: pharmacyStoreEmail, password: pharmacyStorePassword },
  };
}

function pageReadyState(path: string): 'networkidle' | 'domcontentloaded' {
  return ['/lab', '/pharmacy', '/pharmacy-hod', '/pharmacy-store'].includes(path)
    ? 'domcontentloaded'
    : 'networkidle';
}

test.describe('Role dashboard smoke', () => {
  const creds = requireCredentials();
  const cases: RoleDashboardCase[] = [
    {
      label: 'RECEPTION',
      path: '/reception',
      heading: /Reception Dashboard/i,
      supportHeading: { name: 'Follow-Ups', exact: true },
      creds: creds.reception,
    },
    {
      label: 'CHEW',
      path: '/anc',
      heading: /ANC (Dashboard|Care Workspace)/i,
      supportHeading: { name: /ANC Queue/i },
      creds: creds.chew,
    },
    {
      label: 'MIDWIFE',
      path: '/maternity',
      heading: /Maternity (Dashboard|Care Workspace)/i,
      supportHeading: { name: /Maternity Queue/i },
      creds: creds.midwife,
    },
    {
      label: 'DOCTOR',
      path: '/doctor',
      heading: /Doctor Dashboard/i,
      supportHeading: { name: 'Patient Queue', exact: true },
      creds: creds.doctor,
    },
    {
      label: 'LAB',
      path: '/lab',
      heading: /Laboratory Workspace/i,
      supportHeading: { name: /Chemical Pathology Bench/i },
      creds: creds.lab,
    },
    {
      label: 'PHARMACY',
      path: '/pharmacy',
      heading: /Pharmacy Dispensing Workspace/i,
      supportHeading: { name: 'Ready to Dispense', exact: true },
      creds: creds.pharmacy,
    },
    {
      label: 'CMD',
      path: '/cmd',
      heading: /CMD Approval Workspace/i,
      supportHeading: { name: /Supply Approval Queue/i },
      creds: creds.cmd,
    },
    {
      label: 'PHARMACY_HOD',
      path: '/pharmacy-hod',
      heading: /Pharmacy HOD Dashboard/i,
      supportHeading: { name: /Pharmacy Command Center/i },
      creds: creds.pharmacyHod,
    },
    {
      label: 'PHARMACY_STORE_OFFICER',
      path: '/pharmacy-store',
      heading: /Pharmacy Store Dashboard/i,
      creds: creds.pharmacyStore,
    },
  ];

  for (const roleCase of cases) {
    test(`${roleCase.label} dashboard loads without server/runtime failures`, async ({
      browser,
      playwright,
    }) => {
      const { context, page } = await newLoggedInPage(browser, playwright, roleCase.creds);
      const serverFailures: string[] = [];
      const runtimeFailures: string[] = [];
      try {
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

        await page.goto(roleCase.path, { waitUntil: pageReadyState(roleCase.path) });

        await expect(page).toHaveURL(new RegExp(`${roleCase.path}$|${roleCase.path}\\?`));
        await expect(page.getByRole('heading', { name: roleCase.heading })).toBeVisible({
          timeout: 30_000,
        });
        if (roleCase.label === 'LAB') {
          await expect(page.getByTestId('app-header-shell')).toHaveCSS(
            'border-bottom-color',
            'rgb(215, 230, 248)'
          );
          await expect(page.getByTestId('app-header-role-badge')).toHaveCSS(
            'background-color',
            'rgb(234, 244, 251)'
          );
        }
        if (roleCase.supportHeading) {
          await expect(
            page.getByRole('heading', {
              name: roleCase.supportHeading.name,
              exact: roleCase.supportHeading.exact,
            })
          ).toBeVisible();
        }

        expect(serverFailures, `Server failures seen for ${roleCase.label}`).toEqual([]);
        expect(runtimeFailures, `Runtime failures seen for ${roleCase.label}`).toEqual([]);
      } finally {
        await context.close();
      }
    });
  }

  test('LAB request modal shows workflow state, defaults, and completion checklist', async ({
    browser,
    playwright,
  }) => {
    const { context, page } = await newLoggedInPage(browser, playwright, creds.lab);
    const serverFailures: string[] = [];
    const runtimeFailures: string[] = [];
    try {
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

      await page.goto('/lab', { waitUntil: 'domcontentloaded' });

      await expect(
        page.getByRole('heading', { name: /Laboratory Workspace/i })
      ).toBeVisible({ timeout: 30_000 });
      await expect(
        page.getByRole('heading', { name: /Chemical Pathology Bench/i })
      ).toBeVisible();
      await expect(page.getByTestId('lab-bench-unit-chip')).toBeVisible();
      await expect(page.getByTestId('lab-selected-unit-persistent-chip')).toBeVisible();
      await expect(page.getByTestId('lab-bench-attention-strip')).toBeVisible();
      await expect(page.getByTestId('lab-tab-badge-queue')).toBeVisible();
      await page.getByTestId('lab-tab-results').click();
      await expect(
        page.getByRole('heading', { name: 'Result Workbench', exact: true })
      ).toBeVisible();
      await page.getByTestId('lab-tab-queue').click();
      await expect(
        page.getByRole('heading', { name: 'Paid Queue', exact: true })
      ).toBeVisible();

      const queueRow = page.getByRole('row').filter({
        hasText: 'Playwright Lab Workflow Patient',
      });
      await expect(queueRow).toBeVisible({ timeout: 30_000 });
      const openButton = queueRow.getByRole('button', { name: 'Open' });
      await expect(openButton).toBeVisible({ timeout: 30_000 });
      await openButton.click();

      await expect(page.getByTestId('lab-request-modal')).toBeVisible();
      await expect(page.getByTestId('lab-request-modal-title')).toContainText('Lab Request:');
      await expect(
        page.getByRole('button', { name: 'Request Details', exact: true })
      ).toBeVisible();
      await expect(
        page.getByRole('button', { name: 'Result Entry', exact: true })
      ).toBeVisible();
      await expect(
        page.getByRole('button', { name: 'Completion', exact: true })
      ).toBeVisible();
      await expect(page.getByTestId('lab-selected-unit-chip')).toBeVisible();
      await expect(page.getByTestId('lab-configured-template-badge')).toBeVisible();
      await expect(page.getByTestId('lab-specimen-type-input')).toHaveValue('Blood');
      await expect(page.getByTestId('lab-specimen-source-input')).toHaveValue('Blood');

      await page.getByRole('button', { name: 'Completion', exact: true }).click();
      await expect(page.getByTestId('lab-completion-checklist')).toBeVisible();
      await expect(page.getByText('Paid request')).toBeVisible();
      await expect(
        page.getByText(
          'A received specimen is required before this lab request can be completed.'
        )
      ).toBeVisible();

      expect(serverFailures, 'Server failures seen for LAB modal workflow').toEqual([]);
      expect(runtimeFailures, 'Runtime failures seen for LAB modal workflow').toEqual([]);
    } finally {
      await context.close();
    }
  });

  test('LAB completion succeeds without a false failure when visit transition follows', async ({
    browser,
    playwright,
  }) => {
    const { context, page } = await newLoggedInPage(browser, playwright, creds.lab);
    const serverFailures: string[] = [];
    const runtimeFailures: string[] = [];
    try {
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

      await page.goto('/lab', { waitUntil: 'domcontentloaded' });

      await expect(
        page.getByRole('heading', { name: /Laboratory Workspace/i })
      ).toBeVisible({ timeout: 30_000 });
      await expect(
        page.getByRole('heading', { name: /Chemical Pathology Bench/i })
      ).toBeVisible();
      await page.getByTestId('lab-tab-results').click();
      await expect(
        page.getByRole('heading', { name: 'Result Workbench', exact: true })
      ).toBeVisible();

      const completionRow = page.getByRole('row').filter({
        hasText: 'Playwright Lab Completion Patient',
      });
      await expect(completionRow).toBeVisible({ timeout: 30_000 });
      await completionRow.getByRole('button', { name: 'Open' }).click();

    await expect(page.getByTestId('lab-request-modal')).toBeVisible();
    await page.getByRole('button', { name: 'Completion', exact: true }).click();
    await expect(page.getByTestId('lab-completion-checklist')).toBeVisible();
    await expect(page.getByText('Result released')).toBeVisible();

    const startCompletionButton = page.getByRole('button', { name: 'Start Completion' });
    await expect(startCompletionButton).toBeEnabled({ timeout: 30_000 });
    await startCompletionButton.click();

    await expect(page.getByText('Lab Request Completed')).toBeVisible({ timeout: 30_000 });
    await expect(
      page.getByRole('button', { name: 'Update Visit Status', exact: true })
    ).toBeVisible();
    await expect(page.getByText('Failed to complete lab request')).toHaveCount(0);

    await page.getByRole('button', { name: 'Update Visit Status', exact: true }).click();
    await expect(page.getByText('Workflow Complete')).toBeVisible({ timeout: 30_000 });
    await expect(
      page.getByText('Visit status transitioned to LAB_COMPLETED')
    ).toBeVisible();

      expect(serverFailures, 'Server failures seen for LAB completion workflow').toEqual([]);
      expect(runtimeFailures, 'Runtime failures seen for LAB completion workflow').toEqual([]);
    } finally {
      await context.close();
    }
  });
});
