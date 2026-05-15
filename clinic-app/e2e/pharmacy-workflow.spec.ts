import { expect, test } from '@playwright/test';
import { newLoggedInPage } from './support/auth';

type Credentials = {
  email: string;
  password: string;
};

type WorkflowConfig = {
  patientName: string;
  batchNumber: string;
  prescribedQuantity: number;
  firstDispenseQuantity: number;
  remainingAfterPartial: number;
  expectedFinalStockQuantity: number;
};

function deriveRoleEmail(email: string, suffix: string): string {
  const [local, domain] = email.split('@');
  return `${local}+${suffix}@${domain}`;
}

function requireCredentials(): {
  cashier: Credentials;
  pharmacy: Credentials;
} {
  const receptionEmail = process.env.E2E_RECEPTION_EMAIL || '';
  const receptionPassword = process.env.E2E_RECEPTION_PASSWORD || '';
  const cashierEmail =
    process.env.E2E_CASHIER_EMAIL || deriveRoleEmail(receptionEmail, 'cashier');
  const cashierPassword = process.env.E2E_CASHIER_PASSWORD || receptionPassword;
  const pharmacyEmail =
    process.env.E2E_PHARMACY_EMAIL || deriveRoleEmail(receptionEmail, 'pharmacy');
  const pharmacyPassword = process.env.E2E_PHARMACY_PASSWORD || receptionPassword;

  if (!receptionEmail || !receptionPassword) {
    test.skip(
      true,
      'Set E2E_RECEPTION_EMAIL and E2E_RECEPTION_PASSWORD to run pharmacy workflow E2E.'
    );
  }

  return {
    cashier: { email: cashierEmail, password: cashierPassword },
    pharmacy: { email: pharmacyEmail, password: pharmacyPassword },
  };
}

function requireWorkflowConfig(): WorkflowConfig {
  const patientName =
    process.env.E2E_PHARMACY_WORKFLOW_PATIENT_NAME ||
    'Playwright Pharmacy Workflow Patient';
  const batchNumber =
    process.env.E2E_PHARMACY_WORKFLOW_BATCH_NUMBER || 'PW-PHARM-001';
  const initialStockQuantity = Number(
    process.env.E2E_PHARMACY_WORKFLOW_STOCK_QUANTITY || '40'
  );
  const prescribedQuantity = Number(
    process.env.E2E_PHARMACY_WORKFLOW_PRESCRIBED_QUANTITY || '10'
  );
  const firstDispenseQuantity = Number(
    process.env.E2E_PHARMACY_WORKFLOW_DISPENSE_QUANTITY || '5'
  );

  if (
    Number.isNaN(initialStockQuantity) ||
    Number.isNaN(prescribedQuantity) ||
    Number.isNaN(firstDispenseQuantity) ||
    initialStockQuantity <= 0 ||
    prescribedQuantity <= 0 ||
    firstDispenseQuantity <= 0 ||
    firstDispenseQuantity >= prescribedQuantity ||
    prescribedQuantity >= initialStockQuantity
  ) {
    throw new Error(
      'Invalid pharmacy workflow stock configuration. Check E2E_PHARMACY_WORKFLOW_STOCK_QUANTITY, E2E_PHARMACY_WORKFLOW_PRESCRIBED_QUANTITY, and E2E_PHARMACY_WORKFLOW_DISPENSE_QUANTITY.'
    );
  }

  return {
    patientName,
    batchNumber,
    prescribedQuantity,
    firstDispenseQuantity,
    remainingAfterPartial: prescribedQuantity - firstDispenseQuantity,
    expectedFinalStockQuantity: initialStockQuantity - prescribedQuantity,
  };
}

function workflowRow(page: import('@playwright/test').Page, patientName: string) {
  return page.getByRole('row').filter({ hasText: patientName }).first();
}

function dispensingSidebarButton(
  page: import('@playwright/test').Page,
  label: string
) {
  return page.locator('aside').getByRole('button', { name: new RegExp(`^${label}\\b`) });
}

test.describe('Pharmacy workflow E2E', () => {
  const creds = requireCredentials();
  const workflow = requireWorkflowConfig();

  test('cashier payment unlocks dispensing, supports partial dispense, and deducts local stock', async ({
    browser,
    playwright,
  }) => {
    const { context: pharmacyContext, page: pharmacyPage } = await newLoggedInPage(
      browser,
      playwright,
      creds.pharmacy
    );
    const { context: cashierContext, page: cashierPage } = await newLoggedInPage(
      browser,
      playwright,
      creds.cashier
    );

    try {
      await test.step('Pharmacy sees seeded prescription awaiting payment clearance', async () => {
        await pharmacyPage.goto('/pharmacy', { waitUntil: 'domcontentloaded' });

        await expect(
          pharmacyPage.getByRole('heading', { name: 'Pharmacy Dispensing Workspace' })
        ).toBeVisible({ timeout: 30_000 });

        await dispensingSidebarButton(pharmacyPage, 'Awaiting Payment Clearance').click();
        await pharmacyPage.getByLabel('Search queue').fill(workflow.patientName);

        const awaitingRow = workflowRow(pharmacyPage, workflow.patientName);
        await expect(awaitingRow).toBeVisible({ timeout: 30_000 });
        await expect(awaitingRow).toContainText('Paracetamol');
        await expect(awaitingRow).toContainText('Awaiting Payment Clearance');
      });

      await test.step('Cashier settles the pharmacy charge and gets destination hint', async () => {
        await cashierPage.goto('/cashier', { waitUntil: 'domcontentloaded' });

        await expect(
          cashierPage.getByRole('heading', { name: 'Cashier Financial Workstation' })
        ).toBeVisible({ timeout: 30_000 });

        await cashierPage.getByRole('button', { name: 'Pharmacy Charges' }).click();
        await expect(
          cashierPage.getByRole('heading', { name: 'Pharmacy Charges' })
        ).toBeVisible();

        await cashierPage.getByLabel('Search', { exact: true }).fill(workflow.patientName);
        await cashierPage.getByRole('button', { name: 'Refresh' }).click();

        const chargeRow = workflowRow(cashierPage, workflow.patientName);
        await expect(chargeRow).toBeVisible({ timeout: 30_000 });
        await expect(chargeRow).toContainText('UNPAID');
        await expect(chargeRow).toContainText(
          'Awaiting Payment Clearance — Adult Pharmacy'
        );

        await chargeRow.click();
        await expect(
          cashierPage.getByRole('heading', { name: 'Payment Collection' })
        ).toBeVisible();
        await expect(
          cashierPage.getByText(`Patient: ${workflow.patientName}`)
        ).toBeVisible();
        await expect(cashierPage.getByText('1 item(s) selected')).toBeVisible();
        await expect(
          cashierPage.getByRole('button', { name: 'Pay Pharmacy Charges' })
        ).toBeEnabled();

        const networkEvents: string[] = [];
        const consoleEvents: string[] = [];
        const requestLogger = (request: import('@playwright/test').Request) => {
          if (request.url().includes('/billing')) {
            networkEvents.push(`request ${request.method()} ${request.url()}`);
          }
        };
        const responseLogger = (response: import('@playwright/test').Response) => {
          if (response.url().includes('/billing')) {
            networkEvents.push(
              `response ${response.status()} ${response.request().method()} ${response.url()}`
            );
          }
        };
        const requestFailedLogger = (request: import('@playwright/test').Request) => {
          if (request.url().includes('/billing')) {
            networkEvents.push(
              `requestfailed ${request.method()} ${request.url()} ${request.failure()?.errorText || 'unknown'}`
            );
          }
        };
        const consoleLogger = (message: import('@playwright/test').ConsoleMessage) => {
          if (message.type() === 'error' || message.text().toLowerCase().includes('billing')) {
            consoleEvents.push(`${message.type()}: ${message.text()}`);
          }
        };
        const pageErrorLogger = (error: Error) => {
          consoleEvents.push(`pageerror: ${error.message}`);
        };

        cashierPage.on('request', requestLogger);
        cashierPage.on('response', responseLogger);
        cashierPage.on('requestfailed', requestFailedLogger);
        cashierPage.on('console', consoleLogger);
        cashierPage.on('pageerror', pageErrorLogger);

        let payResponse: import('@playwright/test').Response;
        try {
          const payResponsePromise = cashierPage.waitForResponse(
            (response) =>
              response.url().includes('/v1/billing/pay') &&
              response.request().method() === 'POST',
            { timeout: 30_000 }
          );
          await cashierPage
            .getByRole('button', { name: 'Pay Pharmacy Charges' })
            .click();
          payResponse = await payResponsePromise;
        } catch (error) {
          throw new Error(
            [
              `Cashier payment request did not complete: ${String(error)}`,
              `Network events: ${networkEvents.join(' | ') || 'none'}`,
              `Console events: ${consoleEvents.join(' | ') || 'none'}`,
            ].join('\n')
          );
        } finally {
          cashierPage.off('request', requestLogger);
          cashierPage.off('response', responseLogger);
          cashierPage.off('requestfailed', requestFailedLogger);
          cashierPage.off('console', consoleLogger);
          cashierPage.off('pageerror', pageErrorLogger);
        }

        const payResponseBody = await payResponse.text();
        expect(
          payResponse.ok(),
          `Expected cashier payment request to succeed, got ${payResponse.status()}: ${payResponseBody}`
        ).toBeTruthy();

        const confirmation = cashierPage.getByTestId('cashier-payment-confirmation');
        await expect(confirmation).toBeVisible({ timeout: 30_000 });
        await expect(confirmation).toContainText('Payment confirmed');
        await expect(confirmation).toContainText(
          'Ready for Pharmacy Dispense — Adult Pharmacy'
        );
      });

      await test.step('Pharmacy sees the item unlocked live and dispenses from local stock', async () => {
        await dispensingSidebarButton(pharmacyPage, 'Ready to Dispense').click();
        await pharmacyPage.getByLabel('Search queue').fill(workflow.patientName);

        const readyRow = workflowRow(pharmacyPage, workflow.patientName);
        await expect(readyRow).toBeVisible({ timeout: 30_000 });
        await expect(readyRow).toContainText(/Ready to Dispense/i);

        await readyRow.getByRole('button', { name: 'View' }).click();
        await expect(pharmacyPage.getByText('Payment cleared')).toBeVisible();
        await expect(
          pharmacyPage.getByText('Local Unit Stock', { exact: true })
        ).toBeVisible();
        await expect(
          pharmacyPage.getByRole('button', { name: 'Open Dispense Bench' })
        ).toBeEnabled();
        await pharmacyPage.getByRole('button', { name: 'Open Dispense Bench' }).click();

        await expect(pharmacyPage.getByTestId('pharmacy-dispense-bench')).toBeVisible();
        await expect(pharmacyPage.getByText('Local Stock Validation')).toBeVisible();
        await expect(
          pharmacyPage.getByTestId('pharmacy-batch-select')
        ).toContainText(workflow.batchNumber);

        await pharmacyPage
          .getByTestId('pharmacy-dispense-quantity')
          .fill(String(workflow.firstDispenseQuantity));
        await pharmacyPage.getByRole('button', { name: 'Dispense Medication' }).click();

        const workflowFlash = pharmacyPage.getByTestId('pharmacy-workflow-flash');
        await expect(workflowFlash).toBeVisible({ timeout: 30_000 });
        await expect(workflowFlash).toContainText('Partial dispense recorded');

        await dispensingSidebarButton(pharmacyPage, 'Ready to Dispense').click();
        await pharmacyPage.getByLabel('Search queue').fill(workflow.patientName);
        const partialRow = workflowRow(pharmacyPage, workflow.patientName);
        await expect(partialRow).toBeVisible({ timeout: 30_000 });
        await expect(partialRow).toContainText('Partially Dispensed');
        await expect(partialRow).toContainText(
          `${workflow.remainingAfterPartial} remaining`
        );

        await partialRow.getByRole('button', { name: 'Bench' }).click();
        await expect(pharmacyPage.getByTestId('pharmacy-dispense-bench')).toBeVisible();
        await pharmacyPage
          .getByTestId('pharmacy-dispense-quantity')
          .fill(String(workflow.remainingAfterPartial));
        await pharmacyPage.getByRole('button', { name: 'Dispense Medication' }).click();

        await expect(workflowFlash).toBeVisible({ timeout: 30_000 });
        await expect(workflowFlash).toContainText('Dispense completed');

        await dispensingSidebarButton(pharmacyPage, 'Dispensed Today').click();
        await pharmacyPage.getByLabel('Search queue').fill(workflow.patientName);
        const dispensedRow = workflowRow(pharmacyPage, workflow.patientName);
        await expect(dispensedRow).toBeVisible({ timeout: 30_000 });
        await expect(dispensedRow).toContainText('Dispensed');

        await dispensingSidebarButton(pharmacyPage, 'Local Stock').click();
        const stockRow = pharmacyPage.getByRole('row').filter({
          hasText: workflow.batchNumber,
        });
        await expect(stockRow).toBeVisible({ timeout: 30_000 });
        await expect(stockRow).toContainText('Paracetamol');
        await expect(stockRow).toContainText(
          String(workflow.expectedFinalStockQuantity)
        );
      });
    } finally {
      await pharmacyContext.close();
      await cashierContext.close();
    }
  });
});
