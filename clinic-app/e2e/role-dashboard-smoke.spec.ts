import { expect, test } from '@playwright/test';

const apiBase = process.env.E2E_API_BASE_URL || 'http://localhost:8000/api';

type Credentials = { email: string; password: string };

type RoleDashboardCase = {
  label: string;
  path: string;
  heading: RegExp;
  supportHeading?: {
    name: string | RegExp;
    exact?: boolean;
  };
  creds: Credentials;
};

function deriveRoleEmail(email: string, suffix: string): string {
  const [local, domain] = email.split('@');
  return `${local}+${suffix}@${domain}`;
}

function requireCredentials(): {
  reception: Credentials;
  chew: Credentials;
  midwife: Credentials;
  doctor: Credentials;
  lab: Credentials;
  pharmacy: Credentials;
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
      heading: /Lab Dashboard/i,
      supportHeading: { name: 'Lab Requests', exact: true },
      creds: creds.lab,
    },
    {
      label: 'PHARMACY',
      path: '/pharmacy',
      heading: /Pharmacy Dashboard/i,
      supportHeading: { name: 'Prescription Queue', exact: true },
      creds: creds.pharmacy,
    },
  ];

  for (const roleCase of cases) {
    test(`${roleCase.label} dashboard loads without server/runtime failures`, async ({
      page,
    }) => {
      const serverFailures: string[] = [];
      const runtimeFailures: string[] = [];
      page.on('response', (response) => {
        if (!response.url().includes('/api/')) {
          return;
        }
        if (response.status() >= 500) {
          serverFailures.push(`${response.status()} ${response.request().method()} ${response.url()}`);
        }
      });
      page.on('pageerror', (error) => {
        runtimeFailures.push(error.message);
      });

      await loginApi(page.request, roleCase.creds);
      await page.goto(roleCase.path, { waitUntil: 'networkidle' });

      await expect(page).toHaveURL(new RegExp(`${roleCase.path}$|${roleCase.path}\\?`));
      await expect(page.getByRole('heading', { name: roleCase.heading })).toBeVisible({
        timeout: 30_000,
      });
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
    });
  }
});
