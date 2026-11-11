import { test, expect, type Page } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
async function login(page: Page, email: string) {
  await page.goto('/#/entrar');
  await page.getByLabel('E-mail', { exact: true }).fill(email);
  await page.getByLabel('Senha', { exact: true }).fill('Senha de teste UC03 123');
  await page.getByRole('button', { name: 'Continuar', exact: true }).click();
  await page.getByRole('link', { name: 'Matrículas', exact: true }).click();
}
test('UC04: autoinscrição, busca, duplicata, confirmação e remoção', async ({ page, request }) => {
  const token = (
    await (
      await request.post('http://127.0.0.1:5001/api/v1/auth/login', {
        data: { email_usuario: 'professora@example.com', senha: 'Senha de teste UC03 123' },
      })
    ).json()
  ).data.access_token;
  const headers = { Authorization: `Bearer ${token}` };
  const teacher = (
    await (await request.get('http://127.0.0.1:5001/api/v1/usuarios/me', { headers })).json()
  ).data;
  const turma = (
    await (
      await request.post('http://127.0.0.1:5001/api/v1/turmas', {
        headers,
        data: {
          periodo_letivo: '2026/2',
          codigo_turma: 'ESTSI04',
          nivel_turma: 1,
          id_curso: 1,
          id_docente_responsavel: teacher.id_usuario,
        },
      })
    ).json()
  ).data;
  await login(page, 'estudante@example.com');
  await page.getByLabel('Código de acesso da turma', { exact: true }).fill(turma.codigo_acesso);
  await page.getByRole('button', { name: 'Confirmar inscrição', exact: true }).click();
  await expect(page.getByRole('status')).toHaveText('Estudante matriculado com sucesso!');
  await page.getByRole('button', { name: 'Sair da conta' }).click();
  await login(page, 'professora@example.com');
  await page
    .getByLabel('Turma para gerenciar matrículas', { exact: true })
    .selectOption(String(turma.id_turma));
  await page.getByLabel('Buscar por nome, matrícula ou e-mail', { exact: true }).fill('0002026');
  await page.getByRole('button', { name: 'Buscar estudante', exact: true }).click();
  await page.getByRole('button', { name: 'Matricular Estudante de Teste', exact: true }).click();
  await expect(page.getByRole('alert')).toContainText('já está matriculado');
  await page.getByRole('button', { name: 'Remover Estudante de Teste', exact: true }).click();
  await expect(page.getByRole('button', { name: 'Confirmar remoção', exact: true })).toBeDisabled();
  await page
    .getByLabel('Confirmação da remoção', { exact: true })
    .fill('Estudante de Teste/ESTSI04');
  await page.getByLabel('Motivo da remoção', { exact: true }).fill('Matrícula na turma incorreta');
  await page.getByRole('button', { name: 'Confirmar remoção', exact: true }).click();
  await expect(page.getByRole('status')).toContainText(
    'O estudante foi removido da turma com sucesso!',
  );
  await page.getByRole('button', { name: 'Matricular Estudante de Teste', exact: true }).click();
  await expect(page.getByRole('status')).toHaveText('Estudante matriculado com sucesso!');
  expect(
    (await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze())
      .violations,
  ).toEqual([]);
  await page.screenshot({ path: 'test-results/uc04-desktop.png', fullPage: true });
  await page.setViewportSize({ width: 390, height: 844 });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(
    true,
  );
  await page.screenshot({ path: 'test-results/uc04-mobile.png', fullPage: true });
});
