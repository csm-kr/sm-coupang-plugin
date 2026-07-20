import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

import {
  PROJECT_ID_PATTERN,
  STAGES,
  buildCodexPrompt,
  confirmSourcingSelection,
  createDefaultProjectId,
  createInitialState,
  deriveProgress,
  formatCodexEvent,
  formatOptionalMultiple,
  formatOptionalPercent,
  formatOptionalWon,
  isRunActive,
  normalizeSourcingReport,
  reportHref,
  selectSourcingCandidate,
  shouldRefreshProjectAfterRun,
  sourcingReportJsonHrefs,
  stageActionCopy,
  setStageApproval,
  setStageCompleted,
  updateStageInput,
  validateImportedState,
} from "./workflow.js";

const appSource = readFileSync(new URL("./App.jsx", import.meta.url), "utf8");
const stylesSource = readFileSync(new URL("./styles.css", import.meta.url), "utf8");

function fillSourcing(state) {
  const values = {
    category: "가구/생활/취미",
    maxUnitSupplyPrice: "5000",
    minMarkupMultiple: "3",
  };
  return Object.entries(values).reduce(
    (next, [field, value]) => updateStageInput(next, "sourcing", field, value, "2026-07-17T00:00:00Z"),
    state,
  );
}

test("nine beginner-facing stages start at sourcing and lock future work", () => {
  const progress = deriveProgress(createInitialState("2026-07-17T00:00:00Z"));
  assert.equal(STAGES.length, 9);
  assert.equal(progress.currentStageId, "sourcing");
  assert.equal(progress.stages[0].status, "current");
  assert.equal(progress.stages[1].status, "locked");
});

test("required inputs unlock completion and advance exactly one stage", () => {
  const ready = fillSourcing(createInitialState("2026-07-17T00:00:00Z"));
  const completed = setStageCompleted(ready, "sourcing", true, "2026-07-17T00:00:00Z");
  const progress = deriveProgress(completed);
  assert.equal(progress.stages[0].status, "completed");
  assert.equal(progress.currentStageId, "handoff");
  assert.equal(progress.completedCount, 1);
});

test("category is optional and an empty value selects the full Best pool", () => {
  const category = STAGES.find((stage) => stage.id === "sourcing").inputs.find((input) => input.id === "category");
  assert.equal(category.required, false);

  const ready = updateStageInput(fillSourcing(createInitialState()), "sourcing", "category", "");
  const completed = setStageCompleted(ready, "sourcing", true);
  assert.equal(deriveProgress(completed).currentStageId, "handoff");

  const prompt = buildCodexPrompt(ready, "sourcing");
  assert.match(prompt, /도매꾹 Best 전체·6개 대분류/);
  assert.match(prompt, /미입력 필수 항목: 없음/);
  assert.match(prompt, /설명만 하지 말고 실제 조사를 실행/);
  assert.match(prompt, /설정한 최소 가격 배수 이상인 pair가 하나라도/);
  assert.match(prompt, /더 싼 등록은 탈락 근거로 사용하지 않는다/);
  assert.match(prompt, /리뷰 또는 100명 이상 만족/);
  assert.match(prompt, /links\.reportRuns/);
});

test("sourcing inputs match pair discovery instead of budget and target margin planning", () => {
  const inputs = STAGES.find((stage) => stage.id === "sourcing").inputs;

  assert.deepEqual(inputs.map((input) => input.id), [
    "category",
    "maxUnitSupplyPrice",
    "minMarkupMultiple",
  ]);
  assert.equal(inputs.find((input) => input.id === "category").required, false);
  assert.equal(inputs.find((input) => input.id === "maxUnitSupplyPrice").suffix, "원");
  assert.equal(inputs.find((input) => input.id === "minMarkupMultiple").suffix, "배");
});

test("explicit approval gates cannot be completed by filled fields alone", () => {
  let state = setStageCompleted(fillSourcing(createInitialState()), "sourcing", true);
  for (const [field, value] of Object.entries({
    candidateId: "C-007",
    productName: "샘플 상품",
    supplierUrl: "https://example.com/item",
    approvedPrice: "12900",
  })) {
    state = updateStageInput(state, "handoff", field, value);
  }
  state = setStageCompleted(state, "handoff", true);
  assert.equal(deriveProgress(state).currentStageId, "handoff");

  state = setStageApproval(state, "handoff", true);
  state = setStageCompleted(state, "handoff", true);
  assert.equal(deriveProgress(state).currentStageId, "product-planning");
});

test("generated prompt names one specialist skill and includes known inputs", () => {
  const state = fillSourcing(createInitialState());
  const prompt = buildCodexPrompt(state, "sourcing");
  assert.match(prompt, /\$coupang-commerce-automation:coupang-best-high-markup-sourcing/);
  assert.match(prompt, /가구\/생활\/취미/);
  assert.match(prompt, /다음 한 단계만/);
  assert.doesNotMatch(prompt, /coupang-content-studio/);
});

test("import keeps known data and rejects incompatible schemas", () => {
  const state = fillSourcing(createInitialState());
  assert.equal(validateImportedState(JSON.parse(JSON.stringify(state))).stageData.sourcing.inputs.category, "가구/생활/취미");
  assert.throws(
    () => validateImportedState({ ...state, schemaVersion: "2.0.0" }),
    /지원하지 않는 상태 파일/,
  );
});

test("project identifiers require three safe path characters", () => {
  assert.match("abc", PROJECT_ID_PATTERN);
  assert.doesNotMatch("a", PROJECT_ID_PATTERN);
  assert.doesNotMatch("../outside", PROJECT_ID_PATTERN);
});

test("a beginner gets a valid project id without typing an English slug", () => {
  const projectId = createDefaultProjectId(new Date("2026-07-17T02:30:45.123Z"));

  assert.equal(projectId, "project-20260717-023045-123");
  assert.match(projectId, PROJECT_ID_PATTERN);
});

test("codex JSON events become readable embedded console lines", () => {
  assert.equal(
    formatCodexEvent({ type: "item.started", item: { type: "command_execution", command: "npm test" } }),
    "$ npm test",
  );
  assert.equal(
    formatCodexEvent({ type: "item.completed", item: { type: "agent_message", text: "작업을 마쳤습니다." } }),
    "작업을 마쳤습니다.",
  );
  assert.match(formatCodexEvent({ type: "turn.completed", usage: { output_tokens: 42 } }), /42/);
});

test("only queued running and stopping codex runs are active", () => {
  assert.equal(isRunActive({ status: "queued" }), true);
  assert.equal(isRunActive({ status: "running" }), true);
  assert.equal(isRunActive({ status: "stopping" }), true);
  assert.equal(isRunActive({ status: "succeeded" }), false);
  assert.equal(isRunActive(null), false);
});

test("a terminal codex run refreshes project report links", () => {
  assert.equal(shouldRefreshProjectAfterRun({ status: "succeeded" }), true);
  assert.equal(shouldRefreshProjectAfterRun({ status: "failed" }), true);
  assert.equal(shouldRefreshProjectAfterRun({ status: "stopped" }), true);
  assert.equal(shouldRefreshProjectAfterRun({ status: "running" }), false);
  assert.equal(shouldRefreshProjectAfterRun(null), false);
});

test("only workspace report paths become clickable dashboard links", () => {
  assert.equal(
    reportHref("reports/2026/2026-07-19/sample/report.html"),
    "/reports/2026/2026-07-19/sample/report.html",
  );
  assert.equal(reportHref("../STATUS.md"), null);
  assert.equal(reportHref("https://example.com/report.html"), null);
});

test("unknown candidate prices and margins never look like verified zero values", () => {
  assert.equal(formatOptionalWon(null), "확인 대기");
  assert.equal(formatOptionalWon(""), "확인 대기");
  assert.equal(formatOptionalWon(1200), "1,200원");
  assert.equal(formatOptionalPercent(undefined), "확인 대기");
  assert.equal(formatOptionalPercent(0), "0.0%");
  assert.equal(formatOptionalMultiple(null), "확인 대기");
  assert.equal(formatOptionalMultiple(3.25), "3.25배");
});

test("linked sourcing reports become inline candidate data sources without opening each report", () => {
  assert.deepEqual(
    sourcingReportJsonHrefs([
      "reports/2026/2026-07-19/older/high-markup-report.html",
      "reports/2026/2026-07-19/latest/high-markup-report.html",
      "../outside/report.html",
    ]),
    [
      "/reports/2026/2026-07-19/latest/high-markup-report.json",
      "/reports/2026/2026-07-19/older/high-markup-report.json",
    ],
  );

  const report = normalizeSourcingReport({
    status: "RESEARCH_EXPANSION_REQUIRED",
    sourcing_decision: "PRICE_REVIEW_BLOCKED",
    candidates: [
      {
        candidate_id: "66252064",
        name: "발 아치 운동화 깔창",
        wholesale_url: "https://domeggook.com/66252064",
        supplier_terms: {
          unit_supply_price: 1200,
          minimum_order_qty: 5,
          wholesale_shipping_total: 3000,
        },
        verified_identical_one_unit_market_price_range: { count: 0, min: null, max: null },
        profitability_range: { low: null, high: null },
        decision: "PRICE_REVIEW_BLOCKED",
        blockers: ["EXACT_IDENTITY_UNVERIFIED", "ORDER_INCREMENT_UNVERIFIED"],
      },
    ],
  }, "/reports/2026/2026-07-19/latest/high-markup-report.json");

  assert.equal(report.candidates.length, 1);
  assert.deepEqual(report.candidates[0], {
    candidateId: "66252064",
    productName: "발 아치 운동화 깔창",
    supplierUrl: "https://domeggook.com/66252064",
    unitSupplyPrice: 1200,
    minimumOrderQuantity: 5,
    wholesaleShippingTotal: 3000,
    recommendedPrice: null,
    marketPriceMin: null,
    marketPriceMax: null,
    marketEvidenceCount: 0,
    marginLow: null,
    marginHigh: null,
    coupangProductName: "",
    coupangUrl: "",
    currentSalePrice: null,
    markupMultiple: null,
    salesEvidenceLabel: "",
    sourceDecision: "PRICE_REVIEW_BLOCKED",
    blockers: ["EXACT_IDENTITY_UNVERIFIED", "ORDER_INCREMENT_UNVERIFIED"],
    selectable: false,
    reportPath: "reports/2026/2026-07-19/latest/high-markup-report.json",
  });
});

test("one candidate click and one confirmation save the choice and advance to product planning", () => {
  let state = setStageCompleted(fillSourcing(createInitialState()), "sourcing", true);
  const { candidates: [candidate] } = normalizeSourcingReport({
    status: "QUALIFIED",
    qualified_candidates: [
      {
        candidate_id: "C-007",
        name: "검증된 샘플 상품",
        wholesale_url: "https://example.com/supplier/C-007",
        supplier_terms: {
          unit_supply_price: 3500,
          minimum_order_qty: 2,
          wholesale_shipping_total: 3000,
        },
        recommended_price: 12900,
        market_price_range: { count: 7, min: 11900, max: 14900 },
        profitability_range: {
          low: { margin_pct: 40.2 },
          high: { margin_pct: 48.1 },
        },
        decision: "SHORTLIST",
        blockers: [],
      },
    ],
  }, "/reports/2026/2026-07-19/latest/qualified-candidates.json");

  state = selectSourcingCandidate(state, candidate, "12900", "2026-07-19T10:00:00Z");
  assert.equal(state.stageData.handoff.inputs.candidateId, "C-007");
  assert.equal(state.stageData.handoff.inputs.approvedPrice, "12900");
  assert.equal(state.stageData.handoff.approved, false);
  assert.equal(state.stageData.handoff.selection.reportPath, "reports/2026/2026-07-19/latest/qualified-candidates.json");

  state = confirmSourcingSelection(state, "2026-07-19T10:01:00Z");
  assert.equal(state.stageData.handoff.approved, true);
  assert.equal(state.stageData.handoff.completed, true);
  assert.equal(deriveProgress(state).currentStageId, "product-planning");
});

test("blocked discovery candidates remain reviewable but cannot cross the handoff gate", () => {
  const state = setStageCompleted(fillSourcing(createInitialState()), "sourcing", true);
  const blocked = {
    candidateId: "BLOCKED-1",
    productName: "추가 조사 후보",
    supplierUrl: "https://example.com/blocked",
    recommendedPrice: null,
    sourceDecision: "PRICE_REVIEW_BLOCKED",
    blockers: ["EXACT_IDENTITY_UNVERIFIED"],
    selectable: false,
    reportPath: "reports/2026/2026-07-19/blocked/report.json",
  };

  assert.throws(
    () => selectSourcingCandidate(state, blocked, "9900"),
    /전체 소싱 검증을 통과한 SHORTLIST 후보만 선택/,
  );
  assert.equal(deriveProgress(state).currentStageId, "handoff");
});

test("the primary action copy keeps users focused on exactly one next task", () => {
  const state = createInitialState("2026-07-20T00:00:00Z");
  const progress = deriveProgress(state);
  const current = progress.stages.find((stage) => stage.status === "current");
  const locked = progress.stages.find((stage) => stage.status === "locked");

  assert.deepEqual(stageActionCopy(current, null), {
    action: "run",
    label: "Codex로 소싱 시작",
    helper: "입력값을 저장한 뒤 현재 단계만 실행합니다.",
  });
  assert.deepEqual(stageActionCopy(current, { status: "running" }), {
    action: "monitor",
    label: "소싱 작업 진행 중",
    helper: "실행 로그에서 조사와 파일 생성 상태를 확인하세요.",
  });
  assert.deepEqual(stageActionCopy(locked, null), {
    action: "locked",
    label: "앞 단계를 먼저 완료하세요",
    helper: "필수 입력과 승인 게이트를 통과하면 자동으로 열립니다.",
  });
});

test("a discovery report normalizes the qualifying wholesale-coupang pair for comparison", () => {
  const report = normalizeSourcingReport({
    status: "DISCOVERY_MATCHES_FOUND",
    matches: [{
      candidate_id: "BEST-003",
      name: "도매꾹 생활용품",
      wholesale_url: "https://domeggook.com/300",
      unit_supply_price: 3000,
      decision: "HIGH_MARKUP_DISCOVERY",
      qualifying_pairs: [{
        wholesale_name: "도매꾹 생활용품",
        wholesale_url: "https://domeggook.com/300",
        unit_supply_price: 3000,
        coupang_name: "쿠팡 판매 상품",
        coupang_url: "https://www.coupang.com/vp/products/900",
        current_sale_price: 12000,
        markup_multiple: 4,
        sales_evidence: { type: "satisfaction_badge", count: 100, label: "100명 이상 만족했어요" },
      }],
    }],
  }, "/reports/2026/2026-07-20/pairs/high-markup-report.json");

  assert.equal(report.candidates[0].unitSupplyPrice, 3000);
  assert.equal(report.candidates[0].coupangProductName, "쿠팡 판매 상품");
  assert.equal(report.candidates[0].coupangUrl, "https://www.coupang.com/vp/products/900");
  assert.equal(report.candidates[0].currentSalePrice, 12000);
  assert.equal(report.candidates[0].markupMultiple, 4);
  assert.equal(report.candidates[0].salesEvidenceLabel, "100명 이상 만족했어요");
});

test("the handoff UI describes an evidence-backed pair rather than a market-low comparison", () => {
  assert.match(appSource, /도매꾹 ↔ 쿠팡 pair/);
  assert.match(appSource, /가격 배수/);
  assert.match(appSource, /판매 근거/);
  assert.match(appSource, /낮은 가격의 다른 등록은 이 pair를 탈락시키지 않습니다/);
});

test("the dashboard exposes a commerce color system and accessible workflow navigation", () => {
  assert.match(stylesSource, /--commerce-blue:\s*#2563eb/i);
  assert.match(stylesSource, /--commerce-red:\s*#e5484d/i);
  assert.match(stylesSource, /--surface-canvas:\s*#f5f7fa/i);
  assert.match(stylesSource, /\.flow-summary\s*\{/);
  assert.match(stylesSource, /\.workflow-overview\s*\{/);
  assert.match(appSource, /className=\{`flow-summary/);
  assert.match(appSource, /<FlowSummary\s/);
  assert.match(appSource, /aria-label="전체 워크플로 진행률"/);
  assert.match(appSource, /aria-current=\{selectedId === stage\.id \? "step" : undefined\}/);
  assert.match(appSource, /role="progressbar"/);
  assert.match(appSource, /aria-valuenow=\{progress\.percentage\}/);
});
