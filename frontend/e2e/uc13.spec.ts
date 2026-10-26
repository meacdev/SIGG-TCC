import { expect, test } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

test('UC13: matriz, histórico, filtro e confirmação de cobrança em todas as páginas', async ({
  page,
}) => {
  await page.goto('/#/entrar');
  await page.getByLabel('E-mail', { exact: true }).fill('professora@example.com');
  await page.getByLabel('Senha', { exact: true }).fill('Senha de teste UC03 123');
  await page.getByRole('button', { name: 'Entrar', exact: true }).click();
  await page.getByRole('link', { name: 'Monitorar Prazos', exact: true }).click();
  await page
    .getByLabel('Turma de TCC', { exact: true })
    .selectOption({ label: 'ESTVAZIA13 · 2026/2 · TCC 1' });
  await expect(page.getByRole('status')).toContainText('Nenhum estudante cadastrado ou localizado');
  await expect(
    page.getByRole('button', { name: 'Disparar Notificação de Cobrança', exact: true }),
  ).toBeDisabled();
  await page
    .getByLabel('Turma de TCC', { exact: true })
    .selectOption({ label: 'ESTATIVA13 · 2026/2 · TCC 1' });
  await expect(page.getByRole('status')).toContainText('Nenhum estudante com inatividade superior');
  await page
    .getByLabel('Turma de TCC', { exact: true })
    .selectOption({ label: 'ESTSI13 · 2026/2 · TCC 1' });
  await expect(page.getByText('Inativo > 30 dias', { exact: true })).toHaveCount(20);
  await page.getByRole('button', { name: 'Disparar Notificação de Cobrança', exact: true }).click();
  await expect(page.getByRole('alert')).toContainText('Selecione ao menos um estudante');
  await page.getByRole('button', { name: 'Aluno Monitoramento 01', exact: true }).click();
  await expect(page.getByRole('dialog')).toContainText('Revisar os objetivos do trabalho.');
  await page.screenshot({ path: 'test-results/uc13-historico.png' });
  await page.getByRole('button', { name: 'Fechar histórico', exact: true }).click();
  await page.getByLabel('Status', { exact: true }).selectOption('inativos');
  await expect(page.getByText('Página 1 de 2', { exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Selecionar Todos em Atraso', exact: true }).click();
  await expect(
    page.getByText('21 selecionado(s) em todas as páginas', { exact: true }),
  ).toBeVisible();
  await page.getByRole('button', { name: 'Próxima', exact: true }).click();
  await expect(
    page.getByRole('checkbox', { name: /Selecionar Aluno Monitoramento 21/ }),
  ).toBeChecked();
  await page.getByRole('button', { name: 'Disparar Notificação de Cobrança', exact: true }).click();
  await expect(page.getByRole('dialog')).toContainText('21 destinatário(s) selecionado(s).');
  await expect(page.getByRole('dialog')).toContainText('Identificamos mais de 30 dias');
  await page.screenshot({ path: 'test-results/uc13-confirmacao.png' });
  await page.getByRole('button', { name: 'Cancelar', exact: true }).click();
  await expect(page.getByRole('dialog')).toHaveCount(0);
  await page.getByRole('button', { name: 'Disparar Notificação de Cobrança', exact: true }).click();
  await page.getByRole('button', { name: 'Enviar E-mails', exact: true }).click();
  await expect(page.getByRole('status')).toContainText(
    'Alertas enviados com sucesso aos estudantes selecionados!',
  );
  await expect(
    page.getByText('Resultado do lote: 21 enviado(s), 0 pendente(s), 0 cancelado(s).', {
      exact: true,
    }),
  ).toBeVisible();
  await page.getByRole('button', { name: 'Anterior', exact: true }).click();
  await expect(page.getByText('Página 1 de 2', { exact: true })).toBeVisible();
  expect(
    (await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze())
      .violations,
  ).toEqual([]);
  await page.screenshot({ path: 'test-results/uc13-desktop.png', fullPage: true });
  await page.screenshot({ path: 'test-results/uc13-matriz.png' });
  await page.setViewportSize({ width: 390, height: 844 });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(
    true,
  );
  await page.screenshot({ path: 'test-results/uc13-mobile.png', fullPage: true });
});

test('UC13: estudante não acessa o painel de monitoramento', async ({ page }) => {
  await page.goto('/#/entrar');
  await page.getByLabel('E-mail', { exact: true }).fill('estudante@example.com');
  await page.getByLabel('Senha', { exact: true }).fill('Senha de teste UC03 123');
  await page.getByRole('button', { name: 'Entrar', exact: true }).click();
  await page.getByRole('link', { name: 'Monitorar Prazos', exact: true }).click();
  await expect(page.getByRole('alert')).toContainText('Você não possui permissão');
  await expect(page.getByLabel('Turma de TCC', { exact: true })).toHaveCount(0);
});
