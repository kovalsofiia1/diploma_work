import { expect, test } from '@playwright/test';

const adminEmail = 'e2e-admin@example.com';
const adminPassword = 'AdminPassword123!';
const applicantEmail = 'e2e-applicant@example.com';
const targetUserEmail = 'e2e-user@example.com';
const eventName = 'E2E Admin Event';

test('admin moderates an application, user, and event and sees the audit trail', async ({ page }) => {
  await page.goto('/auth');
  await page.locator('ion-input[formcontrolname="email"] input').fill(adminEmail);
  await page.locator('ion-input[formcontrolname="password"] input').fill(adminPassword);
  await page.locator('ion-button.submit-btn').click();
  await expect(page.getByRole('link', { name: 'Адмін' })).toBeVisible();

  await page.goto('/tabs/admin');
  await expect(page.getByRole('heading', { name: 'Адмін-панель' })).toBeVisible();

  const application = page.locator('app-admin-applications .item').filter({ hasText: applicantEmail });
  await expect(application).toContainText('Очікує');
  await application.locator('ion-button').filter({ hasText: 'Схвалити' }).click();
  const approveDialog = page.locator('ion-alert').filter({ hasText: 'Схвалити заявку?' });
  await approveDialog.locator('button').filter({ hasText: 'Схвалити' }).click();
  await expect(application).toHaveCount(0);

  await page.locator('ion-segment-button').filter({ hasText: 'Користувачі' }).click();
  const user = page.locator('app-admin-users .item').filter({ hasText: targetUserEmail });
  await expect(user).toContainText('Активний');
  await user.locator('ion-button').filter({ hasText: 'Заблокувати' }).click();
  const blockDialog = page.locator('ion-alert').filter({ hasText: `Заблокувати ${targetUserEmail}?` });
  await blockDialog.locator('textarea').fill('E2E moderation reason');
  await blockDialog.locator('button').filter({ hasText: 'Заблокувати' }).click();
  await expect(user).toContainText('Заблокований');
  await expect(user).toContainText('E2E moderation reason');

  await page.locator('ion-segment-button').filter({ hasText: 'Події' }).click();
  const event = page.locator('app-admin-events .item').filter({ hasText: eventName });
  await expect(event).toContainText('Видима');
  await event.locator('ion-button').filter({ hasText: 'Приховати' }).click();
  const hideDialog = page.locator('ion-alert').filter({ hasText: 'Приховати подію' });
  await hideDialog.locator('textarea').fill('E2E moderation reason');
  await hideDialog.locator('button').filter({ hasText: 'Приховати' }).click();
  await expect(event).toContainText('Приховано');
  await expect(event).toContainText('E2E moderation reason');

  await page.locator('ion-segment-button').filter({ hasText: 'Журнал' }).click();
  const auditLog = page.locator('app-admin-audit-log');
  await expect(auditLog).toContainText('Схвалено заявку організатора');
  await expect(auditLog).toContainText('Заблоковано користувача');
  await expect(auditLog).toContainText('Приховано подію');
  await expect(auditLog).toContainText(adminEmail);
  await expect(auditLog).toContainText('E2E moderation reason');
});
