import { test, expect, type Page } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
async function login(page: Page, email: string) {
  await page.goto('/#/entrar');
  await page.getByLabel('E-mail', { exact: true }).fill(email);
  await page.getByLabel('Senha', { exact: true }).fill('Senha de teste UC03 123');
  await page.getByRole('button', { name: 'Continuar', exact: true }).click();
  await page.getByRole('link', { name: 'Trabalhos', exact: true }).click();
}
test('UC06: artigo publicado, nível herdado, edição e aceite do orientador', async ({
  page,
  request,
}) => {
  const api = 'http://127.0.0.1:5001/api/v1';
  const teacher = (
    await (
      await request.post(api + '/auth/login', {
        data: { email_usuario: 'professora@example.com', senha: 'Senha de teste UC03 123' },
      })
    ).json()
  ).data;
  const student = (
    await (
      await request.post(api + '/auth/login', {
        data: { email_usuario: 'estudante@example.com', senha: 'Senha de teste UC03 123' },
      })
    ).json()
  ).data;
  const headers = { Authorization: `Bearer ${teacher.access_token}` };
  const turma = (
    await (
      await request.post(api + '/turmas', {
        headers,
        data: {
          periodo_letivo: '2026/2',
          codigo_turma: 'ESTSI06',
          nivel_turma: 2,
          id_curso: 1,
          id_docente_responsavel: teacher.usuario.id_usuario,
        },
      })
    ).json()
  ).data;
  const added = await request.post(api + `/turmas/${turma.id_turma}/matriculas`, {
    headers,
    data: { id_aluno: student.usuario.id_usuario },
  });
  expect(added.status()).toBe(201);
  const membership = (await added.json()).data.id_matricula;
  await login(page, 'estudante@example.com');
  await page
    .getByLabel('Título do trabalho', { exact: true })
    .fill('Pesquisa sobre qualidade de software');
  await page.getByLabel('Área de interesse / Tema', { exact: true }).fill('Engenharia de software');
  await page.getByLabel('Turma vinculada', { exact: true }).selectOption(String(membership));
  await expect(page.getByLabel('Nível da disciplina', { exact: true })).toHaveValue('TCC 2');
  await expect(page.getByLabel('Nível da disciplina', { exact: true })).toHaveAttribute(
    'readonly',
    '',
  );
  await page
    .getByLabel('Orientador', { exact: true })
    .selectOption({ label: 'Professora de Teste' });
  await page.getByLabel('Modalidade do trabalho', { exact: true }).selectOption('artigo');
  await page.getByRole('button', { name: 'Salvar trabalho', exact: true }).click();
  await expect(page.getByLabel('Tipo de artigo', { exact: true })).toHaveAttribute(
    'aria-invalid',
    'true',
  );
  await page.getByLabel('Tipo de artigo', { exact: true }).selectOption('publicado');
  await page.getByLabel('Link/URL do artigo', { exact: true }).fill('https://example.com/artigo');
  await page.getByLabel('DOI do artigo', { exact: true }).fill('inválido');
  await page.getByRole('button', { name: 'Salvar trabalho', exact: true }).click();
  await expect(page.getByRole('alert')).toContainText('DOI válido');
  await page.getByLabel('DOI do artigo', { exact: true }).fill('10.1234/software');
  await page.getByRole('button', { name: 'Salvar trabalho', exact: true }).click();
  await expect(page.getByRole('status')).toHaveText('Trabalho registrado com sucesso!');
  await expect(page.getByText('Situação: pendente', { exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Sair da conta' }).click();
  await login(page, 'professora@example.com');
  await page
    .getByRole('button', { name: 'Abrir Pesquisa sobre qualidade de software', exact: true })
    .click();
  await page.getByRole('button', { name: 'Aceitar orientação', exact: true }).click();
  await expect(page.getByRole('status')).toHaveText('Resposta de orientação registrada.');
  await page.getByRole('button', { name: 'Sair da conta' }).click();
  await login(page, 'estudante@example.com');
  await expect(page.getByText(/Situação: aceito/)).toBeVisible();
  await page.getByLabel('Subtítulo (opcional)', { exact: true }).fill('Um estudo aplicado');
  await page.getByRole('button', { name: 'Salvar trabalho', exact: true }).click();
  await expect(page.getByRole('status')).toHaveText('Trabalho registrado com sucesso!');
  expect(
    (await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze())
      .violations,
  ).toEqual([]);
  await page.screenshot({ path: 'test-results/uc06-desktop.png', fullPage: true });
  await page.setViewportSize({ width: 390, height: 844 });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(
    true,
  );
  await page.screenshot({ path: 'test-results/uc06-mobile.png', fullPage: true });
});
