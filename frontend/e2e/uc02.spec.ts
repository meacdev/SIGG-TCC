import { expect, test } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

const oldPassword = 'Senha antiga de teste 123';
const newPassword = 'Senha nova de teste 456';

test('UC02: recupera por e-mail, valida o código e entra com a nova senha', async ({
  page,
  request,
}, testInfo) => {
  const email = `recuperacao-${crypto.randomUUID()}@example.com`;
  expect(
    (
      await request.post('http://127.0.0.1:5001/api/v1/usuarios', {
        data: {
          nome_usuario: 'Docente de Teste',
          email_usuario: email,
          senha: oldPassword,
          titulacao_docente: 'mestre',
        },
      })
    ).status(),
  ).toBe(201);
  await page.goto('/#/entrar');
  await page.getByLabel('E-mail', { exact: true }).fill(email);
  await page.getByRole('link', { name: 'Esqueceu senha?' }).click();
  await expect(page).toHaveTitle('Recuperar senha · SIGG-TCC');
  await expect(page.getByLabel('E-mail', { exact: true })).toHaveValue(email);
  await page.screenshot({ path: testInfo.outputPath('uc02-email.png'), fullPage: true });
  await page.getByRole('button', { name: 'Enviar código' }).click();
  await expect(page.getByRole('heading', { name: 'Confira seu e-mail' })).toBeVisible();
  const mail = await (
    await request.get(`http://127.0.0.1:5001/__test__/mail?email=${encodeURIComponent(email)}`)
  ).json();
  const code = /é: ([0-9]{10})\n/.exec(mail.content)?.[1];
  expect(code).toMatch(/^[0-9]{10}$/);
  await page
    .getByLabel('Código de recuperação')
    .fill(code === '0000000000' ? '1111111111' : '0000000000');
  await page.getByRole('button', { name: 'Continuar', exact: true }).click();
  await expect(page.getByRole('alert')).toContainText('Código inválido');
  await page.getByLabel('Código de recuperação').fill(code!);
  await page.screenshot({ path: testInfo.outputPath('uc02-codigo.png'), fullPage: true });
  await page.getByRole('button', { name: 'Continuar', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Crie uma nova senha' })).toBeVisible();
  await page.getByLabel('Nova senha', { exact: true }).fill(newPassword);
  await page.getByLabel('Confirmação de senha', { exact: true }).fill('Diferente 123456');
  await page.getByRole('button', { name: 'Confirmar', exact: true }).click();
  await expect(page.getByRole('alert')).toContainText('Revise os campos');
  await page.getByLabel('Confirmação de senha', { exact: true }).fill(newPassword);
  await page.screenshot({ path: testInfo.outputPath('uc02-nova-senha.png'), fullPage: true });
  await page.getByRole('button', { name: 'Confirmar', exact: true }).click();
  await expect(page).toHaveURL(/#\/entrar$/);
  await expect(page.getByRole('status')).toContainText('Senha redefinida com sucesso!');
  expect(
    await page.evaluate(() => ({ local: localStorage.length, session: sessionStorage.length })),
  ).toEqual({ local: 0, session: 0 });
  await page.getByLabel('Senha', { exact: true }).fill(oldPassword);
  await page.getByRole('button', { name: 'Continuar', exact: true }).click();
  await expect(page.getByRole('alert')).toContainText('E-mail ou senha inválidos');
  await page.getByLabel('Senha', { exact: true }).fill(newPassword);
  await page.getByRole('button', { name: 'Continuar', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Meu cadastro' })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Meu cadastro' })).toHaveCount(1);
  await expect(page.getByRole('navigation', { name: 'Área acadêmica' })).toBeVisible();
  await expect(page.getByRole('status')).toHaveText('Login realizado com sucesso!');
});

test('UC02: conta desconhecida, reenvio, retorno ao login e acessibilidade móvel', async ({
  page,
}, testInfo) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/#/recuperar-senha');
  await expect(page).toHaveTitle('Recuperar senha · SIGG-TCC');
  await page.getByRole('button', { name: 'Enviar código' }).click();
  await expect(page.getByRole('alert')).toContainText('Revise os campos');
  await page.getByLabel('E-mail', { exact: true }).fill('nao-cadastrado@example.com');
  await page.getByRole('button', { name: 'Enviar código' }).click();
  await expect(page.getByRole('heading', { name: 'Confira seu e-mail' })).toBeVisible();
  await page.getByLabel('Código de recuperação').fill('A@12');
  await page.getByRole('button', { name: 'Continuar', exact: true }).click();
  await expect(
    page.getByText('Informe os 10 dígitos do código recebido por e-mail.'),
  ).toBeVisible();
  await page.getByLabel('Código de recuperação').fill('1234567890');
  await page.getByRole('button', { name: 'Continuar', exact: true }).click();
  await expect(page.getByRole('alert')).toContainText('Recuperação inválida ou expirada');
  expect((await new AxeBuilder({ page }).analyze()).violations).toEqual([]);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(
    true,
  );
  await page.screenshot({ path: testInfo.outputPath('uc02-mobile.png'), fullPage: true });
  await page.getByRole('button', { name: 'Solicitar novo código ou alterar e-mail' }).click();
  await expect(page.getByRole('button', { name: /Aguarde .*s para reenviar/ })).toBeDisabled();
  await page.getByRole('link', { name: 'Voltar para o login' }).click();
  await expect(page.getByRole('heading', { name: 'Entre na sua conta' })).toBeVisible();
});

test('UC02: falha no envio e limite de solicitações mantêm a etapa de e-mail', async ({ page }) => {
  await page.goto('/#/recuperar-senha');
  await page.getByLabel('E-mail', { exact: true }).fill('docente@example.com');
  await page.route('**/auth/recuperacao-senha', (route) =>
    route.fulfill({
      status: 503,
      json: {
        error: { code: 'EMAIL_INDISPONIVEL', message: 'Não foi possível enviar o e-mail agora.' },
      },
    }),
  );
  await page.getByRole('button', { name: 'Enviar código' }).click();
  await expect(page.getByRole('alert')).toContainText('Não foi possível enviar o e-mail');
  await page.route('**/auth/recuperacao-senha', (route) =>
    route.fulfill({
      status: 429,
      headers: { 'Retry-After': '60' },
      json: { error: { code: 'LIMITE' } },
    }),
  );
  await page.getByRole('button', { name: 'Enviar código' }).click();
  await expect(page.getByRole('alert')).toContainText('Aguarde 60 segundos');
  await expect(page.getByRole('heading', { name: 'Esqueceu sua senha?' })).toBeVisible();
});
