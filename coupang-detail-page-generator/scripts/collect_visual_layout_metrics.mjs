#!/usr/bin/env node

import fs from "node:fs";
import path from "node:path";
import {fileURLToPath} from "node:url";


const HELP = `브라우저 CDP에서 모듈 순서·이미지 크롭·주장 연결 좌표를 수집합니다.

Usage:
  node collect_visual_layout_metrics.mjs --cdp <endpoint> --url <page-url> --storyboard <json> --output <metrics.json> [options]

Required:
  --cdp          Chrome/Edge DevTools HTTP endpoint
  --url          검수할 HTML URL
  --storyboard   visual-storyboard.json 경로
  --output       visual-layout-metrics.json 저장 경로

Options:
  --viewports    쉼표 구분 폭x높이. 기본값: 360x900,800x1000
  --settle-ms    페이지·스크롤 안정화 대기. 기본값: 250
  --screenshots  viewport별 모듈 캡처 저장 디렉터리
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
    else if (arg === "--storyboard") args.storyboard = argv[++index];
    else if (arg === "--output") args.output = argv[++index];
    else if (arg === "--viewports") args.viewports = argv[++index];
    else if (arg === "--settle-ms") args.settleMs = Number(argv[++index]);
    else if (arg === "--screenshots") args.screenshots = argv[++index];
    else throw new Error(`알 수 없는 옵션: ${arg}`);
  }
  if (args.help) return args;
  for (const key of ["cdp", "url", "storyboard", "output"]) {
    if (!args[key]) throw new Error(`--${key} 값이 필요합니다.`);
  }
  if (!fs.existsSync(path.resolve(args.storyboard))) throw new Error(`storyboard 파일이 없습니다: ${args.storyboard}`);
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

async function preparePage(send, url, viewport, settleMs) {
  await send("Emulation.setDeviceMetricsOverride", {
    width: viewport.width,
    height: viewport.height,
    deviceScaleFactor: 1,
    mobile: viewport.width <= 480,
    screenWidth: viewport.width,
    screenHeight: viewport.height,
  });
  const freshUrl = new URL(url);
  freshUrl.searchParams.set("visual_qa", `${Date.now()}-${viewport.width}`);
  await send("Page.navigate", {url: freshUrl.href});
  await sleep(Math.max(800, settleMs * 3));
  await send("Runtime.evaluate", {expression: "document.documentElement.style.scrollBehavior='auto'"});
  const selectors = await send("Runtime.evaluate", {
    expression: "[...document.querySelectorAll('[data-module-id], [data-module]')].map((el) => el.id).filter(Boolean)",
    returnByValue: true,
  });
  for (const id of selectors.result?.value || []) {
    await send("Runtime.evaluate", {expression: `document.getElementById(${JSON.stringify(id)})?.scrollIntoView()`});
    await sleep(settleMs);
  }
  await send("Runtime.evaluate", {expression: "scrollTo(0,0)"});
  await sleep(settleMs);
  return selectors.result?.value || [];
}

async function captureScreenshots(send, directory, viewport, ids, settleMs) {
  const outputDirectory = path.resolve(directory);
  fs.mkdirSync(outputDirectory, {recursive: true});
  for (const id of ids) {
    await send("Runtime.evaluate", {
      expression: `document.getElementById(${JSON.stringify(id)})?.scrollIntoView({block:'start'})`,
    });
    await sleep(Math.max(800, settleMs));
    const screenshot = await send("Page.captureScreenshot", {
      format: "png",
      fromSurface: true,
      captureBeyondViewport: false,
    });
    const safe = id.replace(/[^a-zA-Z0-9_-]/g, "-");
    fs.writeFileSync(
      path.join(outputDirectory, `visual-${viewport.width}px-${safe}.png`),
      Buffer.from(screenshot.data, "base64"),
    );
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
  const probe = fs.readFileSync(path.join(scriptDirectory, "collect_visual_layout_metrics.js"), "utf8");
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
      const ids = await preparePage(client.send, args.url, viewport, args.settleMs);
      const result = await client.send("Runtime.evaluate", {expression: probe, returnByValue: true});
      if (result.exceptionDetails) throw new Error(`probe 실행 실패: ${JSON.stringify(result.exceptionDetails)}`);
      viewports.push(result.result.value);
      if (args.screenshots) await captureScreenshots(client.send, args.screenshots, viewport, ids, args.settleMs);
    }
    const payload = {
      schema_version: "1.0",
      page: args.url,
      storyboard: path.resolve(args.storyboard),
      captured_at: new Date().toISOString(),
      viewports,
    };
    const output = path.resolve(args.output);
    fs.mkdirSync(path.dirname(output), {recursive: true});
    fs.writeFileSync(output, `${JSON.stringify(payload, null, 2)}\n`, "utf8");
    process.stdout.write(`visual-layout-metrics: ${output}\n`);
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
