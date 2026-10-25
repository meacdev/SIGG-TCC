import { test, expect, type Page } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
async function login(page: Page, email: string) {
  await page.goto('/#/entrar');
  await page.getByLabel('E-mail', { exact: true }).fill(email);
  await page.getByLabel('Senha', { exact: true }).fill('Senha de teste UC03 123');
  await page.getByRole('button', { name: 'Entrar', exact: true }).click();
  await page.getByRole('link', { name: 'Reuniões', exact: true }).click();
}
test('UC05: ata, histórico, notificação e alerta de assiduidade', async ({ page, request }) => {
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
        data: { email_usuario: 'reunioes@example.com', senha: 'Senha de teste UC03 123' },
      })
    ).json()
  ).data;
  const headers = { Authorization: `Bearer ${teacher.access_token}` },
    studentHeaders = { Authorization: `Bearer ${student.access_token}` };
  const turma = (
    await (
      await request.post(api + '/turmas', {
        headers,
        data: {
          periodo_letivo: '2026/2',
          codigo_turma: 'ESTSI05',
          nivel_turma: 1,
          id_curso: 1,
          id_docente_responsavel: teacher.usuario.id_usuario,
        },
      })
    ).json()
  ).data;
  const membership = (
    await (
      await request.post(api + `/turmas/${turma.id_turma}/matriculas`, {
        headers,
        data: { id_aluno: student.usuario.id_usuario },
      })
    ).json()
  ).data.id_matricula;
  const response = await request.put(api + '/meu-trabalho', {
    headers: studentHeaders,
    data: {
      titulo: 'Encontros de orientação',
      tema: 'Pesquisa aplicada',
      modalidade: 'monografia',
      id_curso: 1,
      id_matricula: membership,
      id_orientador: teacher.usuario.id_usuario,
    },
  });
  expect(response.status()).toBe(201);
  const work = (await response.json()).data;
  const accepted = await request.post(
    api + `/orientacoes/${work.orientacoes[0].id_orientacao}/resposta`,
    { headers: { ...headers, 'If-Match': response.headers().etag }, data: { decisao: 'aceito' } },
  );
  expect(accepted.status()).toBe(200);
  await login(page, 'reunioes@example.com');
  await page.getByLabel('Trabalho vinculado', { exact: true }).selectOption(String(work.id_etapa));
  await page.getByLabel('Data do encontro', { exact: true }).fill('31/02/2026');
  await page
    .getByLabel('Resumo dos encaminhamentos', { exact: true })
    .fill('Revisar metodologia e definir próximos passos.');
  await page.getByRole('button', { name: 'Registrar ata', exact: true }).click();
  await expect(page.getByRole('alert')).toContainText('data válida');
  const day = new Date(Date.now() - 40 * 86400000).toLocaleDateString('pt-BR', {
    timeZone: 'America/Manaus',
  });
  await page.getByLabel('Data do encontro', { exact: true }).fill(day);
  await page.getByRole('button', { name: 'Registrar ata', exact: true }).click();
  await expect(page.getByRole('status')).toHaveText('Ata registrada com sucesso!');
  await expect(
    page.getByText('Revisar metodologia e definir próximos passos.', { exact: true }),
  ).toBeVisible();
  expect(
    (await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze())
      .violations,
  ).toEqual([]);
  await page.screenshot({ path: 'test-results/uc05-desktop.png', fullPage: true });
  await page.setViewportSize({ width: 390, height: 844 });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(
    true,
  );
  await page.screenshot({ path: 'test-results/uc05-mobile.png', fullPage: true });
  await page.getByRole('button', { name: 'Sair da conta' }).click();
  await login(page, 'professora@example.com');
  await expect(
    page.getByRole('heading', { name: 'Assiduidade das minhas turmas', exact: true }),
  ).toBeVisible();
  await expect(page.getByText(/Alerta: mais de 30 dias sem encontro/).first()).toBeVisible();
  await page.getByLabel('Trabalho vinculado', { exact: true }).selectOption(String(work.id_etapa));
  await expect(
    page.getByRole('heading', { name: `Encontro de ${day}`, exact: true }),
  ).toBeVisible();
});
