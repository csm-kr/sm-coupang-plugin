#!/usr/bin/env node

import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";


const HELP = `브라우저 CDP에서 실제 줄바꿈 좌표를 수집합니다.

Usage:
  node collect_html_typography_metrics.mjs --cdp <endpoint> --url <page-url> --output <metrics.json> [options]

Required:
  --cdp          Chrome/Edge DevTools HTTP endpoint, 예: http://127.0.0.1:9225
  --url          검수할 HTML URL
  --output       typography-metrics.json 저장 경로

Options:
  --viewports    쉼표 구분 폭x높이. 기본값: 360x900,800x1000
  --settle-ms    페이지·스크롤 안정화 대기. 기본값: 250
  --screenshots  선택 사항. viewport별 모듈 캡처를 저장할 디렉터리
  --help         도움말 표시
`;

const sleep = (milliseconds) => new Promise((resolve) => setTimeout(resolve, milliseconds));

function parseArgs(argv) {
  const args = {viewports: "360x900,800x1000", settleMs: 250};
  for (let index = 0; index < argv.length; index += 1) {
    const arg = argv[index];
    if (arg === "--help" || arg === "-h") args.help = true;
    else if (arg === "--cdp") args.cdp = argv[++index];
    else if (arg === "--url") args.url = argv[++index];
    else if (arg === "--output") args.output = argv[++index];
    else if (arg === "--viewports") args.viewports = argv[++index];
    else if (arg === "--settle-ms") args.settleMs = Number(argv[++index]);
    else if (arg === "--screenshots") args.screenshots = argv[++index];
    else throw new Error(`알 수 없는 옵션: ${arg}`);
  }
  if (args.help) return args;
  for (const key of ["cdp", "url", "output"]) {
    if (!args[key]) throw new Error(`--${key} 값이 필요합니다.`);
  }
  if (!Number.isFinite(args.settleMs) || args.settleMs < 0) throw new Error("--settle-ms는 0 이상의 숫자여야 합니다.");
  args.parsedViewports = args.viewports.split(",").map((token) => {
    const match = token.trim().match(/^(\d+)x(\d+)$/i);
    if (!match) throw new Error(`잘못된 viewport: ${token}`);
    return {width: Number(match[1]), height: Number(match[2])};
  });
  return args;
}

async function waitForCdp(endpoint) {
  let lastError;
  for (let attempt = 0; attempt < 40; attempt += 1) {
    try {
      const response = await fetch(`${endpoint}/json/version`);
      if (response.ok) return;
      lastError = new Error(`CDP 응답 ${response.status}`);
    } catch (error) {
      lastError = error;
    }
    await sleep(100);
  }
  throw new Error(`CDP에 연결하지 못했습니다: ${lastError?.message || endpoint}`);
}

async function openTarget(endpoint) {
  const response = await fetch(`${endpoint}/json/new?about:blank`, {method: "PUT"});
  if (!response.ok) throw new Error(`새 CDP target 생성 실패: ${response.status}`);
  return response.json();
}

async function connect(webSocketDebuggerUrl) {
  const socket = new WebSocket(webSocketDebuggerUrl);
  await new Promise((resolve, reject) => {
    socket.addEventListener("open", resolve, {once: true});
    socket.addEventListener("error", reject, {once: true});
  });
  let sequence = 0;
  const pending = new Map();
  socket.addEventListener("message", (event) => {
    const message = JSON.parse(event.data);
    if (!message.id || !pending.has(message.id)) return;
    const {resolve, reject} = pending.get(message.id);
    pending.delete(message.id);
    if (message.error) reject(new Error(JSON.stringify(message.error)));
    else resolve(message.result);
  });
  return {
    socket,
    send(method, params = {}) {
      return new Promise((resolve, reject) => {
        const id = ++sequence;
        pending.set(id, {resolve, reject});
        socket.send(JSON.stringify({id, method, params}));
      });
    },
  };
}

async function collectViewport(send, probe, url, viewport, settleMs) {
  await send("Emulation.setDeviceMetricsOverride", {
    width: viewport.width,
    height: viewport.height,
    deviceScaleFactor: 1,
    mobile: viewport.width <= 480,
    screenWidth: viewport.width,
    screenHeight: viewport.height,
  });
  const freshUrl = new URL(url);
  freshUrl.searchParams.set("typography_qa", `${Date.now()}-${viewport.width}`);
  await send("Page.navigate", {url: freshUrl.href});
  await sleep(Math.max(700, settleMs * 3));
  await send("Runtime.evaluate", {
    expression: "document.documentElement.style.scrollBehavior='auto'",
  });
  const countResult = await send("Runtime.evaluate", {
    expression: "document.querySelectorAll('[data-module]').length",
    returnByValue: true,
  });
  const moduleCount = Number(countResult.result?.value || 0);
  if (moduleCount) {
    for (let index = 1; index <= moduleCount; index += 1) {
      const id = String(index).padStart(2, "0");
      await send("Runtime.evaluate", {expression: `document.querySelector('#module-${id}')?.scrollIntoView()`});
      await sleep(settleMs);
    }
  } else {
    const heightResult = await send("Runtime.evaluate", {expression: "document.documentElement.scrollHeight", returnByValue: true});
    const scrollHeight = Number(heightResult.result?.value || viewport.height);
    for (let top = 0; top < scrollHeight; top += Math.max(300, Math.floor(viewport.height * 0.75))) {
      await send("Runtime.evaluate", {expression: `scrollTo(0, ${top})`});
      await sleep(settleMs);
    }
  }
  await send("Runtime.evaluate", {
    expression: "document.documentElement.style.scrollBehavior='auto'; scrollTo(0, 0)",
  });
  await sleep(settleMs);
  const result = await send("Runtime.evaluate", {expression: probe, returnByValue: true});
  if (result.exceptionDetails) throw new Error(`probe 실행 실패: ${JSON.stringify(result.exceptionDetails)}`);
  return result.result.value;
}

async function captureModuleScreenshots(send, directory, viewport, settleMs) {
  const selectorsResult = await send("Runtime.evaluate", {
    expression: "[...document.querySelectorAll('[data-module]')].map((element) => `#${element.id}`)",
    returnByValue: true,
  });
  const selectors = selectorsResult.result?.value || [];
  const outputDirectory = path.resolve(directory);
  fs.mkdirSync(outputDirectory, {recursive: true});
  for (const selector of selectors) {
    await send("Runtime.evaluate", {
      expression: `document.querySelector(${JSON.stringify(selector)})?.scrollIntoView({block:'start'});`,
    });
    await sleep(Math.max(800, settleMs));
    const screenshot = await send("Page.captureScreenshot", {
      format: "png",
      fromSurface: true,
      captureBeyondViewport: false,
    });
    const moduleName = selector.replace(/^#/, "").replace(/[^a-zA-Z0-9_-]/g, "-");
    const filename = `typography-${viewport.width}px-${moduleName}.png`;
    fs.writeFileSync(path.join(outputDirectory, filename), Buffer.from(screenshot.data, "base64"));
  }
}

async function main() {
  let args;
  try {
    args = parseArgs(process.argv.slice(2));
  } catch (error) {
    process.stderr.write(`${error.message}\n${HELP}`);
    return 2;
  }
  if (args.help) {
    process.stdout.write(HELP);
    return 0;
  }

  const endpoint = args.cdp.replace(/\/$/, "");
  const scriptDirectory = path.dirname(fileURLToPath(import.meta.url));
  const probe = fs.readFileSync(path.join(scriptDirectory, "collect_html_typography_metrics.js"), "utf8");
  await waitForCdp(endpoint);
  const target = await openTarget(endpoint);
  const client = await connect(target.webSocketDebuggerUrl);
  try {
    await client.send("Page.enable");
    await client.send("Runtime.enable");
    await client.send("Network.enable");
    await client.send("Network.setCacheDisabled", {cacheDisabled: true});
    const viewports = [];
    for (const viewport of args.parsedViewports) {
      const metrics = await collectViewport(client.send, probe, args.url, viewport, args.settleMs);
      viewports.push(metrics);
      if (args.screenshots) {
        await captureModuleScreenshots(client.send, args.screenshots, viewport, args.settleMs);
      }
    }
    const payload = {
      schema_version: "1.0",
      page: args.url,
      captured_at: new Date().toISOString(),
      viewports,
    };
    const output = path.resolve(args.output);
    fs.mkdirSync(path.dirname(output), {recursive: true});
    fs.writeFileSync(output, `${JSON.stringify(payload, null, 2)}\n`, "utf8");
    process.stdout.write(`typography-metrics: ${output} | ${viewports.map((item) => `${item.width}px:${item.elements.length}`).join(" ")}\n`);
    return 0;
  } finally {
    await client.send("Page.close").catch(() => {});
    client.socket.close();
  }
}

try {
  process.exitCode = await main();
} catch (error) {
  process.stderr.write(`${error.stack || error.message}\n`);
  process.exitCode = 1;
}
