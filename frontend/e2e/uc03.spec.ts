import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

test('UC03: cadastro, duplicata, alteração, código e inativação de turma', async ({ page }) => {
  await page.goto('/#/entrar');
  await page.getByLabel('E-mail', { exact: true }).fill('professora@example.com');
  await page.getByLabel('Senha', { exact: true }).fill('Senha de teste UC03 123');
  await page.getByRole('button', { name: 'Entrar', exact: true }).click();
  await page.getByRole('link', { name: 'Turmas', exact: true }).click();
  await page.getByRole('button', { name: 'Cadastrar turma', exact: true }).click();
  await expect(page.getByRole('alert')).toContainText('campos obrigatórios');
  await page.getByLabel('Ano/Semestre letivo', { exact: true }).fill('2026/3');
  await page.getByLabel('Disciplina', { exact: true }).selectOption('1');
  await page.getByLabel('Código da turma', { exact: true }).fill('ESTSI03');
  await page.getByLabel('Curso da turma', { exact: true }).selectOption('1');
  await page
    .getByLabel('Docente responsável', { exact: true })
    .selectOption({ label: 'Professora de Teste' });
  await page.getByRole('button', { name: 'Cadastrar turma', exact: true }).click();
  await expect(page.getByLabel('Ano/Semestre letivo', { exact: true })).toHaveAttribute(
    'aria-invalid',
    'true',
  );
  await page.getByLabel('Ano/Semestre letivo', { exact: true }).fill('2026/2');
  await page.getByRole('button', { name: 'Cadastrar turma', exact: true }).click();
  await expect(page.getByRole('status')).toHaveText('Turma cadastrada com sucesso!');
  const code = await page.locator('.academic-box code').textContent();
  expect(code).toHaveLength(24);
  await page.getByRole('button', { name: 'Gerar novo código de acesso', exact: true }).click();
  await expect(page.locator('.academic-box code')).not.toHaveText(code!);
  await page.getByRole('button', { name: 'Nova turma', exact: true }).click();
  await page.getByLabel('Ano/Semestre letivo', { exact: true }).fill('2026/2');
  await page.getByLabel('Disciplina', { exact: true }).selectOption('1');
  await page.getByLabel('Código da turma', { exact: true }).fill('ESTSI03');
  await page.getByLabel('Curso da turma', { exact: true }).selectOption('1');
  await page
    .getByLabel('Docente responsável', { exact: true })
    .selectOption({ label: 'Professora de Teste' });
  await page.getByRole('button', { name: 'Cadastrar turma', exact: true }).click();
  await expect(page.getByRole('alert')).toContainText('Já existe uma turma');
  await page.getByRole('button', { name: 'Gerenciar ESTSI03', exact: true }).click();
  await page.getByLabel('Código da turma', { exact: true }).fill('ESTSI030');
  await page.getByRole('button', { name: 'Salvar turma', exact: true }).click();
  await expect(page.getByRole('status')).toHaveText('Turma atualizada com sucesso!');
  expect(
    (await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze())
      .violations,
  ).toEqual([]);
  await page.screenshot({ path: 'test-results/uc03-desktop.png', fullPage: true });
  await page.setViewportSize({ width: 390, height: 844 });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(
    true,
  );
  await page.screenshot({ path: 'test-results/uc03-mobile.png', fullPage: true });
  await page.getByRole('button', { name: 'Inativar turma', exact: true }).click();
  await page.getByRole('button', { name: 'Confirmar inativação da turma', exact: true }).click();
  await expect(page.getByRole('status')).toHaveText('Turma inativada com sucesso!');
  await page.getByLabel('Situação das turmas', { exact: true }).selectOption('false');
  await expect(page.getByRole('button', { name: 'Gerenciar ESTSI030', exact: true })).toBeVisible();
});
