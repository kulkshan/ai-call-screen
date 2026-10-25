import { spawn } from "node:child_process";
import { mkdir, mkdtemp, writeFile } from "node:fs/promises";
import os from "node:os";
import path from "node:path";

const repoRoot = path.resolve(import.meta.dirname, "..");
const outputDir = path.join(repoRoot, "docs", "video", "scenes");
const chromePath = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
const port = 9338;
const baseUrl = "https://kulkshan.github.io/ai-call-screen";

await mkdir(outputDir, { recursive: true });
const profileDir = await mkdtemp(path.join(os.tmpdir(), "call-screen-video-"));

const chrome = spawn(
  chromePath,
  [
    "--headless=new",
    "--disable-gpu",
    "--hide-scrollbars",
    "--no-first-run",
    "--disable-background-networking",
    `--remote-debugging-port=${port}`,
    `--user-data-dir=${profileDir}`,
    "--window-size=1440,900",
    "about:blank",
  ],
  { stdio: "ignore", windowsHide: true },
);

const sleep = (milliseconds) =>
  new Promise((resolve) => setTimeout(resolve, milliseconds));

async function getPageTarget() {
  for (let attempt = 0; attempt < 60; attempt += 1) {
    try {
      const response = await fetch(`http://127.0.0.1:${port}/json/list`);
      const targets = await response.json();
      const page = targets.find((target) => target.type === "page");
      if (page?.webSocketDebuggerUrl) return page;
    } catch {
      // Chrome is still starting.
    }
    await sleep(100);
  }
  throw new Error("Chrome DevTools did not become available.");
}

const target = await getPageTarget();
const socket = new WebSocket(target.webSocketDebuggerUrl);
await new Promise((resolve, reject) => {
  socket.addEventListener("open", resolve, { once: true });
  socket.addEventListener("error", reject, { once: true });
});

let nextId = 1;
const pending = new Map();

socket.addEventListener("message", (event) => {
  const message = JSON.parse(event.data);
  if (!message.id || !pending.has(message.id)) return;
  const { resolve, reject } = pending.get(message.id);
  pending.delete(message.id);
  if (message.error) reject(new Error(message.error.message));
  else resolve(message.result);
});

function command(method, params = {}) {
  const id = nextId;
  nextId += 1;
  socket.send(JSON.stringify({ id, method, params }));
  return new Promise((resolve, reject) => {
    pending.set(id, { resolve, reject });
  });
}

async function navigate(url) {
  await command("Page.navigate", { url });
  await sleep(2200);
}

async function evaluate(expression) {
  return command("Runtime.evaluate", {
    expression,
    awaitPromise: true,
    returnByValue: true,
  });
}

async function capture(name) {
  const result = await command("Page.captureScreenshot", {
    format: "png",
    fromSurface: true,
    captureBeyondViewport: false,
  });
  await writeFile(path.join(outputDir, name), Buffer.from(result.data, "base64"));
  process.stdout.write(`${name}\n`);
}

try {
  await command("Page.enable");
  await command("Runtime.enable");
  await command("Emulation.setDeviceMetricsOverride", {
    width: 1440,
    height: 900,
    deviceScaleFactor: 1,
    mobile: false,
  });

  await navigate(`${baseUrl}/`);
  await capture("01-intro.png");

  await evaluate(`
    [...document.querySelectorAll('button')]
      .find((button) => button.textContent.includes('Run Call Screen'))
      ?.click();
  `);
  await sleep(6800);
  await capture("02-decision.png");

  await navigate(`${baseUrl}/lab/`);
  await capture("03-evaluation-top.png");

  await evaluate(`
    document.querySelector('[class*="evidenceGrid"]')
      ?.scrollIntoView({ block: 'start', behavior: 'instant' });
    window.scrollBy(0, -80);
  `);
  await sleep(900);
  await capture("04-metrics.png");

  await evaluate(`
    document.querySelector('[class*="mistakes"]')
      ?.scrollIntoView({ block: 'start', behavior: 'instant' });
    window.scrollBy(0, -80);
  `);
  await sleep(900);
  await capture("05-errors.png");

  await evaluate(`
    [...document.querySelectorAll('*')]
      .find((element) => element.children.length === 0 && element.textContent.trim() === '03 / What comes next')
      ?.scrollIntoView({ block: 'start' });
    window.scrollBy(0, -110);
  `);
  await sleep(500);
  await capture("06-rollout.png");
} finally {
  socket.close();
  chrome.kill();
}
