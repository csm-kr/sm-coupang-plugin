import test from "node:test";
import assert from "node:assert/strict";

import {
  PROJECT_ID_PATTERN,
  STAGES,
  buildCodexPrompt,
  createDefaultProjectId,
  createInitialState,
  deriveProgress,
  formatCodexEvent,
  isRunActive,
  setStageApproval,
  setStageCompleted,
  updateStageInput,
  validateImportedState,
} from "./workflow.js";

function fillSourcing(state) {
  const values = {
    category: "생활용품",
    sourcingMode: "standard",
    budget: "300000",
    targetMargin: "40/30",
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
  assert.match(prompt, /\$coupang-commerce-automation:coupang-product-sourcing/);
  assert.match(prompt, /생활용품/);
  assert.match(prompt, /다음 한 단계만/);
  assert.doesNotMatch(prompt, /coupang-content-studio/);
});

test("import keeps known data and rejects incompatible schemas", () => {
  const state = fillSourcing(createInitialState());
  assert.equal(validateImportedState(JSON.parse(JSON.stringify(state))).stageData.sourcing.inputs.category, "생활용품");
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
