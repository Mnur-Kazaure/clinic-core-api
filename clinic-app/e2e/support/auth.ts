import {
  expect,
  type APIRequestContext,
  type Browser,
  type BrowserContext,
  type Page,
} from '@playwright/test';

const apiBase = process.env.E2E_API_BASE_URL || 'http://127.0.0.1:8110/api';

export type E2ECredentials = {
  email: string;
  password: string;
};

type RequestFactory = {
  request: {
    newContext(options?: {
      extraHTTPHeaders?: Record<string, string>;
    }): Promise<APIRequestContext>;
  };
};

export async function newLoggedInPage(
  browser: Browser,
  playwright: RequestFactory,
  creds: E2ECredentials
): Promise<{ context: BrowserContext; page: Page }> {
  const authRequest = await playwright.request.newContext({
    extraHTTPHeaders: {
      'Content-Type': 'application/json',
    },
  });

  try {
    const response = await authRequest.post(`${apiBase}/v1/auth/login`, {
      data: creds,
    });
    expect(response.ok()).toBeTruthy();

    const storageState = await authRequest.storageState();
    const context = await browser.newContext({ storageState });
    const page = await context.newPage();
    return { context, page };
  } finally {
    await authRequest.dispose();
  }
}

export async function loginContext(
  context: BrowserContext,
  playwright: RequestFactory,
  creds: E2ECredentials
) {
  const authRequest = await playwright.request.newContext({
    extraHTTPHeaders: {
      'Content-Type': 'application/json',
    },
  });

  try {
    const response = await authRequest.post(`${apiBase}/v1/auth/login`, {
      data: creds,
    });
    expect(response.ok()).toBeTruthy();

    const storageState = await authRequest.storageState();
    await context.addCookies(storageState.cookies);
  } finally {
    await authRequest.dispose();
  }
}

export async function assertApiLogin(
  request: APIRequestContext,
  creds: E2ECredentials
) {
  const response = await request.post(`${apiBase}/v1/auth/login`, {
    data: creds,
  });
  expect(response.ok()).toBeTruthy();
}
