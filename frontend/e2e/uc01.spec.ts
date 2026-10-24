import { expect, test, type Page } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

const password = 'Senha de teste UC01 123';
const address = () => `uc01-${crypto.randomUUID()}@example.com`;

async function accessFields(page: Page, email: string) {
  await page.getByLabel('Nome completo').fill('Pessoa de Teste');
  await page.getByLabel('E-mail', { exact: true }).fill(email);
  await page.getByLabel('Senha', { exact: true }).fill(password);
  await page.getByLabel('Confirmar senha', { exact: true }).fill(password);
}

async function teacherSignup(page: Page, email: string) {
  await page.goto('/#/cadastro');
  await page.getByRole('radio', { name: /Sou docente/ }).check();
  await accessFields(page, email);
  await page.getByLabel('Titulação', { exact: true }).selectOption('mestre');
  await page.getByRole('button', { name: 'Criar minha conta' }).click();
}

async function login(page: Page, email: string) {
  await page.getByRole('button', { name: 'Ir para o login' }).click();
  await page.getByLabel('E-mail', { exact: true }).fill(email);
  await page.getByLabel('Senha', { exact: true }).fill(password);
  await page.getByRole('button', { name: 'Entrar', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Meu cadastro' })).toBeVisible();
  await expect(page.getByLabel('Nome completo')).toHaveValue('Pessoa de Teste');
}

test('docente: cadastro, consulta, edição, conflito, alteração de e-mail e inativação', async ({
  page,
  request,
}) => {
  const email = address();
  await teacherSignup(page, email);
  await expect(page.getByRole('status')).toHaveText('Cadastro realizado com sucesso!');
  await login(page, email);
  expect(
    await page.evaluate(() => ({ local: localStorage.length, session: sessionStorage.length })),
  ).toEqual({ local: 0, session: 0 });
  await page.getByLabel('Nome completo').fill('Nome Atualizado');
  await page.getByRole('button', { name: 'Salvar alterações' }).click();
  await expect(page.getByRole('status')).toHaveText('Cadastro atualizado com sucesso!');
  await expect(page.getByLabel('Nome completo')).toHaveValue('Nome Atualizado');

  const tokens = await (
    await request.post('http://127.0.0.1:5001/api/v1/auth/login', {
      data: { email_usuario: email, senha: password },
    })
  ).json();
  const headers = { Authorization: `Bearer ${tokens.data.access_token}` };
  const profile = await request.get('http://127.0.0.1:5001/api/v1/usuarios/me', { headers });
  await request.patch('http://127.0.0.1:5001/api/v1/usuarios/me', {
    headers: { ...headers, 'If-Match': profile.headers().etag },
    data: { nome_usuario: 'Alteração em outra sessão' },
  });
  await page.getByLabel('Nome completo').fill('Tentativa desatualizada');
  await page.getByRole('button', { name: 'Salvar alterações' }).click();
  await expect(page.getByRole('alert')).toContainText('O registro foi alterado');
  await expect(page.getByLabel('Nome completo')).toHaveValue('Tentativa desatualizada');
  await page.getByRole('button', { name: 'Recarregar cadastro' }).click();
  await expect(page.getByLabel('Nome completo')).toHaveValue('Alteração em outra sessão');

  const newEmail = address();
  await page.getByLabel('E-mail', { exact: true }).fill(newEmail);
  await page.getByLabel('Senha atual', { exact: true }).fill(password);
  await page.getByRole('button', { name: 'Salvar alterações' }).click();
  await expect(page.getByRole('status')).toContainText('E-mail atualizado com sucesso');
  await page.getByLabel('E-mail', { exact: true }).fill(newEmail);
  await page.getByLabel('Senha', { exact: true }).fill(password);
  await page.getByRole('button', { name: 'Entrar', exact: true }).click();
  await page.getByRole('button', { name: 'Inativar conta', exact: true }).click();
  await page.getByLabel('Confirme sua senha atual').fill('senha incorreta');
  await page.getByRole('button', { name: 'Confirmar inativação' }).click();
  await expect(page.getByRole('dialog')).toContainText('Confirme sua senha atual.');
  await page.getByRole('button', { name: 'Manter minha conta' }).click();
  await expect(page.getByRole('dialog')).not.toBeVisible();
  await page.getByRole('button', { name: 'Inativar conta', exact: true }).click();
  await page.getByLabel('Confirme sua senha atual').fill(password);
  await page.getByRole('button', { name: 'Confirmar inativação' }).click();
  await expect(page.getByRole('status')).toContainText('Sua conta foi inativada com sucesso.');
  await page.getByLabel('E-mail', { exact: true }).fill(newEmail);
  await page.getByLabel('Senha', { exact: true }).fill(password);
  await page.getByRole('button', { name: 'Entrar', exact: true }).click();
  await expect(page.getByRole('alert')).toContainText('inativa');
});

test('estudante: formulário responsivo, cursos reais e matrícula com zeros', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/#/cadastro');
  await accessFields(page, address());
  await page.getByLabel('Matrícula', { exact: true }).fill(`000${Date.now()}`);
  await page.getByLabel('Curso', { exact: true }).selectOption({ label: 'Sistemas de Informação' });
  expect(await page.getByLabel('Senha', { exact: true }).getAttribute('type')).toBe('password');
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(
    true,
  );
  await page.getByRole('button', { name: 'Criar minha conta' }).click();
  await expect(page.getByRole('status')).toHaveText('Cadastro realizado com sucesso!');
});

test('obrigatoriedade, e-mail duplicado e campos opcionais de docente', async ({ page }) => {
  const email = address();
  await teacherSignup(page, email);
  await expect(page.getByRole('status')).toHaveText('Cadastro realizado com sucesso!');
  await page.goto('/#/entrar');
  await page.goto('/#/cadastro');
  await page.getByRole('radio', { name: /Sou docente/ }).check();
  await page.getByRole('button', { name: 'Criar minha conta' }).click();
  await expect(page.getByRole('alert')).toContainText('Preencha todos os campos obrigatórios');
  await accessFields(page, email);
  await page.getByLabel('Titulação', { exact: true }).selectOption('doutor');
  await page.getByRole('button', { name: 'Criar minha conta' }).click();
  await expect(page.getByRole('alert')).toHaveText('Este endereço de e-mail já está cadastrado.');
  await expect(page.getByLabel('E-mail', { exact: true })).toHaveAttribute('aria-invalid', 'true');
  await expect(page.getByLabel('Nome completo')).toHaveValue('Pessoa de Teste');
});

test('falhas de conexão e de catálogo não confirmam cadastro nem inventam cursos', async ({
  page,
}) => {
  await page.route('**/api/v1/cursos?**', (route) =>
    route.fulfill({ json: { data: [], meta: { pages: 0 } } }),
  );
  await page.goto('/#/cadastro');
  await expect(page.getByText('Nenhum curso ativo disponível.', { exact: false })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Criar minha conta' })).toBeDisabled();
  await page.getByRole('radio', { name: /Sou docente/ }).check();
  await accessFields(page, address());
  await page.getByLabel('Titulação', { exact: true }).selectOption('especialista');
  await page.route('**/api/v1/usuarios', (route) => route.abort());
  await page.getByRole('button', { name: 'Criar minha conta' }).click();
  await expect(page.getByRole('alert')).toContainText('Não foi possível conectar ao servidor');
  await expect(page.getByLabel('Nome completo')).toHaveValue('Pessoa de Teste');
  await expect(page.getByRole('status')).toHaveCount(0);
});

test('revisão visual e acessibilidade WCAG 2.1 AA', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.goto('/#/cadastro');
  await expect(page.getByLabel('Curso', { exact: true })).toBeEnabled();
  await page.screenshot({ path: 'test-results/cadastro-desktop.png', fullPage: true });
  expect(
    (await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze())
      .violations,
  ).toEqual([]);
  await page.getByRole('radio', { name: /Sou docente/ }).check();
  await page.screenshot({ path: 'test-results/cadastro-docente.png', fullPage: true });
  expect(
    (await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze())
      .violations,
  ).toEqual([]);
  await page.setViewportSize({ width: 390, height: 844 });
  await page.screenshot({ path: 'test-results/cadastro-mobile.png', fullPage: true });
  for (const width of [320, 390, 768]) {
    await page.setViewportSize({ width, height: 844 });
    expect(
      await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth),
    ).toBe(true);
  }
  await page.goto('/#/entrar');
  expect(
    (await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze())
      .violations,
  ).toEqual([]);
});
