import { expect, test } from '@playwright/test';
import { newLoggedInPage } from './support/auth';

type Credentials = {
  email: string;
  password: string;
};

type ReturnConfig = {
  itemName: string;
  requestQuantity: number;
};

function deriveRoleEmail(email: string, suffix: string): string {
  const [local, domain] = email.split('@');
  return `${local}+${suffix}@${domain}`;
}

function requireCredentials(): {
  pharmacy: Credentials;
  store: Credentials;
} {
  const receptionEmail = process.env.E2E_RECEPTION_EMAIL || '';
  const receptionPassword = process.env.E2E_RECEPTION_PASSWORD || '';
  const pharmacyEmail =
    process.env.E2E_PHARMACY_EMAIL || deriveRoleEmail(receptionEmail, 'pharmacy');
  const pharmacyPassword = process.env.E2E_PHARMACY_PASSWORD || receptionPassword;
  const storeEmail =
    process.env.E2E_PHARMACY_STORE_EMAIL ||
    deriveRoleEmail(receptionEmail, 'pharmacy-store');
  const storePassword =
    process.env.E2E_PHARMACY_STORE_PASSWORD || receptionPassword;

  if (!receptionEmail || !receptionPassword) {
    test.skip(
      true,
      'Set E2E_RECEPTION_EMAIL and E2E_RECEPTION_PASSWORD to run the pharmacy return E2E.'
    );
  }

  return {
    pharmacy: { email: pharmacyEmail, password: pharmacyPassword },
    store: { email: storeEmail, password: storePassword },
  };
}

function requireReturnConfig(): ReturnConfig {
  const itemName =
    process.env.E2E_PHARMACY_RETURN_ITEM_NAME || 'Playwright Return Flow Commodity';
  const requestQuantity = Number(
    process.env.E2E_PHARMACY_RETURN_REQUEST_QUANTITY || '3'
  );

  if (!itemName || Number.isNaN(requestQuantity) || requestQuantity <= 0) {
    throw new Error(
      'Invalid return workflow configuration. Check E2E_PHARMACY_RETURN_ITEM_NAME and E2E_PHARMACY_RETURN_REQUEST_QUANTITY.'
    );
  }

  return { itemName, requestQuantity };
}

function pharmacySidebarButton(
  page: import('@playwright/test').Page,
  label: string
) {
  return page.locator('aside').getByRole('button', {
    name: new RegExp(`^${label}\\b`),
  });
}

function storeSidebarButton(page: import('@playwright/test').Page, label: string) {
  return page.getByRole('navigation', { name: 'Pharmacy store sections' }).getByRole('button', {
    name: new RegExp(`^${label}\\b`),
  });
}

function mainHeading(
  page: import('@playwright/test').Page,
  name: string | RegExp
) {
  return page.locator('main').getByRole('heading', { name }).last();
}

test.describe('Pharmacy return-to-store workflow', () => {
  const creds = requireCredentials();
  const workflow = requireReturnConfig();

  test('unit submits a linked return request and store receives it back into stock', async ({
    browser,
    playwright,
  }) => {
    test.setTimeout(120_000);

    const { context: pharmacyContext, page: pharmacyPage } = await newLoggedInPage(
      browser,
      playwright,
      creds.pharmacy
    );
    const { context: storeContext, page: storePage } = await newLoggedInPage(
      browser,
      playwright,
      creds.store
    );

    try {
      let returnNumber = '';

      await test.step('Dispensing unit submits a return request from acknowledged issue history', async () => {
        await pharmacyPage.goto('/pharmacy', { waitUntil: 'domcontentloaded' });
        await expect(
          pharmacyPage.getByRole('heading', {
            name: 'Pharmacy Dispensing Workspace',
          })
        ).toBeVisible({ timeout: 30_000 });

        await pharmacySidebarButton(pharmacyPage, 'Refill Requests').click();
        await expect(mainHeading(pharmacyPage, 'Refill Requests')).toBeVisible();

        const returnableVoucherCard = pharmacyPage
          .getByTestId('returnable-voucher-card')
          .filter({
            hasText: `${workflow.itemName}: 8 acknowledged`,
          })
          .first();
        await expect(returnableVoucherCard).toBeVisible({ timeout: 30_000 });
        await returnableVoucherCard.getByTestId('return-to-store-trigger').click();

        await expect(
          pharmacyPage.getByRole('heading', { name: 'Return to Store' })
        ).toBeVisible();
        await pharmacyPage
          .getByLabel('Quantity to Return')
          .fill(String(workflow.requestQuantity));
        await pharmacyPage
          .getByLabel('Return Note')
          .fill('Unused stock returned to store.');
        await pharmacyPage
          .getByRole('button', { name: 'Submit Return Request' })
          .click();

        await expect(
          pharmacyPage.getByTestId('pharmacy-workflow-flash')
        ).toContainText('Return request submitted to store for review.');

        const trackerCard = pharmacyPage
          .locator('div.rounded-2xl.border')
          .filter({ hasText: workflow.itemName })
          .filter({ hasText: 'Pending Store Review' })
          .first();
        await expect(trackerCard).toBeVisible({ timeout: 30_000 });

        const trackerText = (await trackerCard.textContent()) || '';
        const match = trackerText.match(/RT-\d{8}-[A-F0-9]{6}/);
        expect(match, `Expected tracker card to contain a return number: ${trackerText}`).not.toBeNull();
        returnNumber = match![0];
      });

      await test.step('Store reviews the linked return request and receives it back into stock', async () => {
        await storePage.goto('/pharmacy-store', { waitUntil: 'domcontentloaded' });
        await expect(
          storePage.getByRole('heading', { name: 'Pharmacy Store Dashboard' })
        ).toBeVisible({ timeout: 30_000 });

        await storeSidebarButton(storePage, 'Receiving & Acknowledgement').click();
        await expect(
          mainHeading(storePage, 'Receiving & Acknowledgement')
        ).toBeVisible();

        const pendingRow = storePage.getByRole('row').filter({ hasText: returnNumber }).first();
        await expect(pendingRow).toBeVisible({ timeout: 30_000 });
        await expect(pendingRow).toContainText(workflow.itemName);
        await expect(pendingRow).toContainText('RETURN PENDING STORE REVIEW');

        await pendingRow.getByRole('button', { name: 'Review Return' }).click();
        await expect(
          storePage.getByRole('heading', { name: returnNumber })
        ).toBeVisible();

        await storePage
          .getByLabel('Review Note')
          .fill('Accepted back into store stock.');
        await storePage.getByRole('button', { name: 'Accept Return' }).click();
        await expect(storePage.getByText('Return request accepted for store receipt.')).toBeVisible({
          timeout: 30_000,
        });

        const acceptedRow = storePage.getByRole('row').filter({ hasText: returnNumber }).first();
        await expect(acceptedRow).toContainText('RETURN ACCEPTED');
        await acceptedRow.getByRole('button', { name: 'Receive Return' }).click();
        await expect(
          storePage.getByRole('heading', { name: returnNumber })
        ).toBeVisible();

        await storePage
          .getByLabel('Receive Note')
          .fill('Received back into central store.');
        await storePage.getByRole('button', { name: 'Receive Into Store' }).click();
        await expect(storePage.getByText('Returned stock received back into store.')).toBeVisible({
          timeout: 30_000,
        });

        const receivedRow = storePage.getByRole('row').filter({ hasText: returnNumber }).first();
        await expect(receivedRow).toContainText('RETURN RECEIVED');
      });

      await test.step('Both workspaces show the closed return lifecycle and linked RETURN movement', async () => {
        await pharmacyPage.getByRole('button', { name: 'Refresh Workspace' }).click();

        const trackerCard = pharmacyPage
          .locator('div.rounded-2xl.border')
          .filter({ hasText: returnNumber })
          .first();
        await expect(trackerCard).toContainText('Return Received', {
          timeout: 30_000,
        });
        await expect(trackerCard).toContainText(workflow.itemName);

        await storeSidebarButton(storePage, 'Movement History').click();
        await expect(mainHeading(storePage, 'Movement History')).toBeVisible();
        await storePage.getByLabel('Search movement history').fill(returnNumber);

        const movementRow = storePage.getByRole('row').filter({ hasText: returnNumber }).first();
        await expect(movementRow).toBeVisible({ timeout: 30_000 });
        await expect(movementRow).toContainText('RETURN');
        await expect(movementRow).toContainText(workflow.itemName);
        await expect(movementRow).toContainText(`+${workflow.requestQuantity}`);
      });
    } finally {
      await pharmacyContext.close();
      await storeContext.close();
    }
  });
});
