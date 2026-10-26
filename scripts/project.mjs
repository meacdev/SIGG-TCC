import { spawn } from "node:child_process";
import { existsSync } from "node:fs";
import { createServer } from "node:net";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const frontend = resolve(root, "frontend");
const windows = process.platform === "win32";
const python =
  process.env.SIGG_PYTHON ||
  resolve(root, ".venv", windows ? "Scripts/python.exe" : "bin/python");
const [command, ...extra] = process.argv.slice(2);
function moduleFile(relativePath) {
  const local = resolve(frontend, "node_modules", relativePath);
  return existsSync(local) ? local : resolve(root, "node_modules", relativePath);
}
const vite = moduleFile("vite/bin/vite.js");
const vitest = moduleFile("vitest/vitest.mjs");
const tsc = moduleFile("typescript/bin/tsc");
const playwright = moduleFile("@playwright/test/cli.js");

function requireFile(path, instruction) {
  if (!existsSync(path)) throw new Error(instruction);
}

function pythonTask(args) {
  requireFile(
    python,
    "Ambiente Python ausente. Na raiz, execute python -m venv .venv e instale backend/requirements-dev.txt.",
  );
  return { executable: python, args, cwd: root };
}

function nodeTask(path, args) {
  requireFile(
    path,
    "Dependências do front-end ausentes. Execute yarn install --frozen-lockfile na raiz.",
  );
  return { executable: process.execPath, args: [path, ...args], cwd: frontend };
}

function launch(task, group = false) {
  return spawn(task.executable, task.args, {
    cwd: task.cwd,
    stdio: "inherit",
    windowsHide: true,
    detached: group && !windows,
    env: { ...process.env, PYTHONUNBUFFERED: "1", PYTHONUTF8: "1" },
  });
}

async function run(task) {
  const child = launch(task);
  return new Promise((resolveCode, reject) => {
    child.once("error", reject);
    child.once("exit", (code) => resolveCode(code ?? 1));
  });
}

function available(port) {
  return new Promise((resolvePort, reject) => {
    const server = createServer();
    server.once("error", () =>
      reject(
        new Error(
          `A porta ${port} está ocupada. Encerre o servidor anterior antes de iniciar yarn dev.`,
        ),
      ),
    );
    server.listen(port, "127.0.0.1", () => server.close(resolvePort));
  });
}

async function stop(child) {
  if (!child.pid || child.exitCode !== null || child.signalCode !== null)
    return;
  if (windows) {
    await new Promise((done) => {
      const killer = spawn(
        "taskkill",
        ["/PID", String(child.pid), "/T", "/F"],
        { windowsHide: true, stdio: "ignore" },
      );
      killer.once("error", done);
      killer.once("exit", done);
    });
  } else {
    try {
      process.kill(-child.pid, "SIGTERM");
    } catch {
      /* Already stopped. */
    }
  }
}

async function development() {
  // Validate both installations before starting either server.
  const backendTask = pythonTask([
    "-m",
    "flask",
    "--app",
    "backend.app:create_app",
    "run",
    "--debug",
    "--host",
    "127.0.0.1",
    "--port",
    "5000",
  ]);
  const frontendTask = nodeTask(vite, ["--host", "127.0.0.1"]);
  await Promise.all([available(5000), available(5173)]);
  if (await run(pythonTask(["scripts/prepare_dev.py"]))) return 1;
  console.log("\nSIGG-TCC — desenvolvimento local");
  console.log("Aplicação: http://127.0.0.1:5173");
  console.log("API: http://127.0.0.1:5000/api/v1");
  console.log(
    "Ctrl+C encerra os dois servidores. O PostgreSQL deve estar em execução.\n",
  );
  const children = [];
  let stopping = false;
  return new Promise((done) => {
    const shutdown = async (code) => {
      if (stopping) return;
      stopping = true;
      await Promise.all(children.map(stop));
      process.off("SIGINT", onInterrupt);
      process.off("SIGTERM", onTerminate);
      done(code);
    };
    const onInterrupt = () => {
      void shutdown(0);
    };
    const onTerminate = () => {
      void shutdown(0);
    };
    process.once("SIGINT", onInterrupt);
    process.once("SIGTERM", onTerminate);
    for (const [name, task] of [
      ["Back-end", backendTask],
      ["Front-end", frontendTask],
    ]) {
      const child = launch(task, true);
      children.push(child);
      child.once("error", () => {
        console.error(
          `${name}: não foi possível iniciar. Confira as dependências.`,
        );
        void shutdown(1);
      });
      child.once("exit", (code) => {
        if (!stopping) {
          console.error(
            `${name} encerrou (código ${code ?? "interrompido"}). Encerrando o outro servidor.`,
          );
          void shutdown(code || 1);
        }
      });
    }
  });
}

async function main() {
  const flask = ["-m", "flask", "--app", "backend.app:create_app"];
  switch (command) {
    case "dev":
      return development();
    case "dev:backend":
      if (await run(pythonTask(["scripts/prepare_dev.py"]))) return 1;
      return run(
        pythonTask([
          ...flask,
          "run",
          "--debug",
          "--host",
          "127.0.0.1",
          "--port",
          "5000",
          ...extra,
        ]),
      );
    case "dev:frontend":
      return run(nodeTask(vite, ["--host", "127.0.0.1", ...extra]));
    case "env:check":
      return run(pythonTask(["scripts/check_env.py", ...extra]));
    case "env:key":
      return run(
        pythonTask(["-c", "import secrets; print(secrets.token_hex(32))"]),
      );
    case "db:upgrade":
      return run(pythonTask([...flask, "db-upgrade", ...extra]));
    case "db:seed":
      return run(pythonTask([...flask, "seed-perfis", ...extra]));
    case "db:check":
      return run(pythonTask(["scripts/check_env.py", "--database"]));
    case "test:frontend":
      return run(nodeTask(vitest, ["run", ...extra]));
    case "test:watch":
      return run(nodeTask(vitest, [...extra]));
    case "test:backend":
      return run(pythonTask(["-m", "pytest", ...extra]));
    case "test:e2e":
      return run(nodeTask(playwright, ["test", ...extra]));
    case "test": {
      const status = await run(nodeTask(vitest, ["run"]));
      return status || run(pythonTask(["-m", "pytest", ...extra]));
    }
    case "build": {
      const status = await run(nodeTask(tsc, ["-b"]));
      return status || run(nodeTask(vite, ["build", ...extra]));
    }
    case "start:backend":
      return run(
        pythonTask([
          "-m",
          "waitress",
          "--listen=127.0.0.1:5000",
          "--call",
          "backend.app:create_app",
          ...extra,
        ]),
      );
    default:
      throw new Error(
        "Comando desconhecido. Use yarn dev, yarn test, yarn build ou yarn env:check na raiz.",
      );
  }
}

try {
  process.exitCode = await main();
} catch (error) {
  console.error(error.message);
  process.exitCode = 1;
}
