import { expect, test } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

const adminPassword = 'Senha de teste UC14 123';
const invitedPassword = 'Senha do convite UC14 456';

test('UC14: pré-cadastra docente, concede perfil e ativa a conta pelo convite', async ({
  page,
  request,
}, testInfo) => {
  const email = `docente-${crypto.randomUUID().slice(0, 8)}@uea.edu.br`;
  await page.goto('/#/entrar');
  await page.getByLabel('E-mail', { exact: true }).fill('secretaria@uea.edu.br');
  await page.getByLabel('Senha', { exact: true }).fill(adminPassword);
  await page.getByRole('button', { name: 'Continuar', exact: true }).click();
  await expect(page.getByText('Administração · secretaria', { exact: true })).toBeVisible();
  await expect(page.getByRole('link', { name: 'Turmas', exact: true })).toHaveCount(0);
  await page.getByRole('link', { name: 'Usuários', exact: true }).click();
  await expect(page).toHaveTitle('Usuários · SIGG-TCC');
  await expect(page.getByText('Página 1 de 2', { exact: true })).toBeVisible();
  await page.getByLabel('Nome, e-mail ou matrícula', { exact: true }).fill('secretaria');
  await page.getByRole('button', { name: 'Buscar', exact: true }).click();
  await expect(page.getByRole('table')).toHaveAccessibleName('1 usuário(s) encontrado(s)');
  await expect(
    page.getByRole('cell', { name: 'Secretaria de Teste secretaria@uea.edu.br' }),
  ).toBeVisible();

  await page.getByRole('button', { name: 'Pré-cadastrar usuário', exact: true }).click();
  await page.getByRole('radio', { name: 'Docente', exact: true }).check();
  await page.getByLabel('Nome completo', { exact: true }).fill('Docente Convidada UC14');
  await page.getByLabel('E-mail', { exact: true }).fill('docente.uc14@gmail.com');
  await page.getByLabel('Titulação', { exact: true }).selectOption('Doutor');
  await page.getByRole('button', { name: 'Pré-cadastrar e enviar convite', exact: true }).click();
  await expect(page.getByText('Use um e-mail @uea.edu.br.', { exact: true })).toBeVisible();
  await page.getByLabel('E-mail', { exact: true }).fill(email);
  await page.getByRole('button', { name: 'Pré-cadastrar e enviar convite', exact: true }).click();
  await expect(page.getByRole('status')).toContainText('Usuário pré-cadastrado com sucesso!');
  await expect(page.getByRole('heading', { name: /Docente Convidada UC14/ })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Reenviar convite', exact: true })).toBeVisible();

  await page.getByLabel('Perfil', { exact: true }).selectOption('professor_disciplina');
  await page
    .getByRole('form', { name: 'Conceder perfil' })
    .getByLabel('Curso', { exact: true })
    .selectOption({ label: 'Sistemas de Informação' });
  await page.getByRole('button', { name: 'Conceder perfil', exact: true }).click();
  const dialog = page.getByRole('dialog');
  await dialog.getByRole('button', { name: 'Confirmar concessão', exact: true }).click();
  await expect(dialog).toContainText('Informe a justificativa da operação.');
  await dialog.getByLabel('Justificativa', { exact: true }).fill('Docente da disciplina em 2026/2');
  await dialog.getByRole('button', { name: 'Confirmar concessão', exact: true }).click();
  await expect(dialog).toHaveCount(0);
  await expect(page.getByRole('status')).toContainText('Perfil de acesso atualizado com sucesso!');
  await expect(
    page.getByText('Professor(a) da disciplina · Sistemas de Informação', { exact: true }),
  ).toBeVisible();
  await page.screenshot({ path: testInfo.outputPath('uc14-gestao.png'), fullPage: true });
  expect(
    (await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze())
      .violations,
  ).toEqual([]);

  await page.getByRole('button', { name: /Sair da conta/ }).click();
  await expect(page.getByText('Você saiu da sua conta.', { exact: true })).toBeVisible();
  const mail = await (
    await request.get(`http://127.0.0.1:5001/__test__/mail?email=${encodeURIComponent(email)}`)
  ).json();
  const link = /(http\S+#\/aceitar-convite\?token=\S+)/.exec(mail.content)?.[1];
  expect(link).toBeTruthy();
  await page.goto(link!);
  await expect(page.getByRole('heading', { name: 'Ative sua conta' })).toBeVisible();
  await expect(page.getByText(email, { exact: true })).toBeVisible();
  // O token sai do endereço assim que a tela abre.
  expect(page.url()).not.toContain('token=');
  expect(
    (await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze())
      .violations,
  ).toEqual([]);
  await page.getByLabel('Nova senha', { exact: true }).fill(invitedPassword);
  await page.getByLabel('Confirmação de senha', { exact: true }).fill(invitedPassword);
  await page.getByRole('button', { name: 'Ativar minha conta' }).click();
  await expect(page.getByRole('status')).toContainText('Conta ativada com sucesso!');
  await expect(page.getByLabel('E-mail', { exact: true })).toHaveValue(email);
  await page.getByLabel('Senha', { exact: true }).fill(invitedPassword);
  await page.getByRole('button', { name: 'Continuar', exact: true }).click();
  await expect(page.getByRole('link', { name: 'Turmas', exact: true })).toBeVisible();
  await expect(page.getByRole('link', { name: 'Usuários', exact: true })).toHaveCount(0);

  // O mesmo link não ativa a conta de novo.
  await page.getByRole('button', { name: /Sair da conta/ }).click();
  await expect(page.getByText('Você saiu da sua conta.', { exact: true })).toBeVisible();
  await page.goto(link!);
  await expect(page.getByRole('alert')).toContainText('Este convite é inválido');
});
