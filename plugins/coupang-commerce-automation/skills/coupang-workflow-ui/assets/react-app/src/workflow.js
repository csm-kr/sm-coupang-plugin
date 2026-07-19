export const SCHEMA_VERSION = "1.0.0";
export const PROJECT_ID_PATTERN = /^[a-z0-9][a-z0-9-]{1,62}[a-z0-9]$/;
const ACTIVE_RUN_STATUSES = new Set(["queued", "running", "stopping"]);
export const DOMEGGOOK_BEST_CATEGORIES = [
  "전체",
  "패션잡화/화장품",
  "의류/언더웨어",
  "출산/유아동/완구",
  "가구/생활/취미",
  "스포츠/건강/식품",
  "가전/휴대폰/산업",
];

export function createDefaultProjectId(now = new Date()) {
  const timestamp = now.toISOString().replace(/\D/g, "").slice(0, 17);
  return `project-${timestamp.slice(0, 8)}-${timestamp.slice(8, 14)}-${timestamp.slice(14)}`;
}

export function isRunActive(run) {
  return Boolean(run && ACTIVE_RUN_STATUSES.has(run.status));
}

export function shouldRefreshProjectAfterRun(run) {
  return Boolean(run && ["succeeded", "failed", "stopped"].includes(run.status));
}

export function reportHref(path) {
  if (typeof path !== "string" || !path.startsWith("reports/")) return null;
  if (path.includes("..") || path.includes(":") || path.includes("\\")) return null;
  return `/${path}`;
}

export function sourcingReportJsonHrefs(reportRuns) {
  const seen = new Set();
  return [...(Array.isArray(reportRuns) ? reportRuns : [])]
    .reverse()
    .map((path) => {
      const href = reportHref(path);
      if (!href) return null;
      if (href.endsWith(".html")) return href.replace(/\.html$/i, ".json");
      return href.endsWith(".json") ? href : null;
    })
    .filter((href) => href && !seen.has(href) && seen.add(href));
}

function numberOrNull(value) {
  if (value === "" || value === null || value === undefined) return null;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

export function formatOptionalWon(value) {
  const parsed = numberOrNull(value);
  return parsed === null ? "확인 대기" : `${parsed.toLocaleString("ko-KR")}원`;
}

export function formatOptionalPercent(value) {
  const parsed = numberOrNull(value);
  return parsed === null ? "확인 대기" : `${parsed.toFixed(1)}%`;
}

function firstArray(...values) {
  return values.find((value) => Array.isArray(value)) ?? [];
}

function normalizeBlockers(candidate) {
  return firstArray(
    candidate.blockers,
    candidate.shortlist_blockers,
    candidate.decision_reasons,
    candidate.exclusion_reasons,
  ).map((value) => String(value)).filter(Boolean);
}

export function normalizeSourcingReport(payload, sourcePath) {
  const reportPath = typeof sourcePath === "string" ? sourcePath.replace(/^\//, "") : "";
  const rows = [
    ...(Array.isArray(payload?.qualified_candidates) ? payload.qualified_candidates : []),
    ...(Array.isArray(payload?.candidates) ? payload.candidates : []),
    ...(Array.isArray(payload?.matches) ? payload.matches : []),
    ...(Array.isArray(payload?.excluded) ? payload.excluded : []),
  ];
  const seen = new Set();
  const candidates = rows.flatMap((candidate, index) => {
    if (!candidate || typeof candidate !== "object") return [];
    const supplier = candidate.supplier_terms ?? candidate.wholesale ?? {};
    const market = candidate.verified_identical_one_unit_market_price_range
      ?? candidate.market_price_range
      ?? candidate.market?.price_range
      ?? {};
    const profitability = candidate.profitability_range ?? candidate.profitability ?? {};
    const candidateId = String(candidate.candidate_id ?? candidate.id ?? "").trim();
    const productName = String(candidate.name ?? candidate.product_name ?? candidate.title ?? "").trim();
    const supplierUrl = String(
      candidate.wholesale_url ?? supplier.source_url ?? supplier.url ?? candidate.source_url ?? "",
    ).trim();
    const sourceDecision = String(
      candidate.decision ?? candidate.source_decision ?? payload?.sourcing_decision ?? payload?.decision ?? "UNKNOWN",
    ).trim();
    const identity = candidateId || `${productName}:${supplierUrl}:${index}`;
    if (seen.has(identity)) return [];
    seen.add(identity);
    return [{
      candidateId,
      productName,
      supplierUrl,
      unitSupplyPrice: numberOrNull(supplier.unit_supply_price ?? supplier.supply_price ?? candidate.unit_supply_price),
      minimumOrderQuantity: numberOrNull(supplier.minimum_order_qty ?? supplier.moq ?? candidate.minimum_order_qty),
      wholesaleShippingTotal: numberOrNull(
        supplier.wholesale_shipping_total ?? supplier.shipping_total ?? candidate.wholesale_shipping_total,
      ),
      recommendedPrice: numberOrNull(
        candidate.recommended_price
          ?? candidate.recommended_sale_price
          ?? candidate.pricing?.recommended_price
          ?? candidate.pricing?.conservative_sale_price,
      ),
      marketPriceMin: numberOrNull(market.min),
      marketPriceMax: numberOrNull(market.max),
      marketEvidenceCount: numberOrNull(market.count) ?? 0,
      marginLow: numberOrNull(
        profitability.low?.margin_pct ?? candidate.stress_margin_pct ?? candidate.metrics?.stress_margin_pct,
      ),
      marginHigh: numberOrNull(
        profitability.high?.margin_pct ?? candidate.base_margin_pct ?? candidate.metrics?.base_margin_pct,
      ),
      sourceDecision,
      blockers: normalizeBlockers(candidate),
      selectable: sourceDecision === "SHORTLIST" && Boolean(candidateId && productName && supplierUrl),
      reportPath,
    }];
  });
  return {
    status: String(payload?.status ?? "UNKNOWN"),
    decision: String(payload?.sourcing_decision ?? payload?.decision ?? "UNKNOWN"),
    reportPath,
    candidates,
  };
}

export function formatCodexEvent(event) {
  if (!event || typeof event !== "object") return String(event ?? "");
  const item = event.item ?? {};
  if (item.type === "agent_message" && item.text) return item.text;
  if (item.type === "command_execution") {
    const command = item.command || item.command_line || "명령 실행";
    const output = item.aggregated_output || item.output || "";
    return [`$ ${command}`, output].filter(Boolean).join("\n");
  }
  if (item.type === "file_change") return item.path ? `파일 변경: ${item.path}` : "파일을 변경했습니다.";
  if (item.type === "mcp_tool_call") return `도구 호출: ${item.server || "MCP"} ${item.tool || ""}`.trim();
  if (item.type === "reasoning" && item.text) return item.text;
  if (event.type === "thread.started") return `Codex 세션 시작 · ${event.thread_id || "ID 확인 중"}`;
  if (event.type === "turn.started") return "작업을 시작했습니다.";
  if (event.type === "turn.completed") {
    const tokens = event.usage?.output_tokens;
    return tokens === undefined ? "작업이 완료됐습니다." : `작업이 완료됐습니다. · 출력 ${tokens} tokens`;
  }
  if (event.type === "turn.failed") return `작업 실패: ${event.error?.message || event.message || "원인을 확인해 주세요."}`;
  if (event.type === "error") return `오류: ${event.message || event.error || "알 수 없는 오류"}`;
  if (event.type === "console") return event.text || "";
  return JSON.stringify(event, null, 2);
}

const field = (id, label, type = "text", extra = {}) => ({ id, label, type, required: true, ...extra });

export const STAGES = [
  {
    id: "sourcing",
    step: "01",
    title: "상품 소싱",
    shortTitle: "소싱",
    summary: "팔 수 있는 후보를 근거와 마진으로 먼저 거릅니다.",
    availability: "ready",
    skill: "coupang-product-sourcing",
    inputs: [
      field("category", "찾고 싶은 카테고리", "select", {
        required: false,
        options: DOMEGGOOK_BEST_CATEGORIES.map((category) => [category, category]),
      }),
      field("budget", "초기 매입 예산", "number", { placeholder: "300000", suffix: "원" }),
      field("targetMargin", "목표 마진 기준", "select", {
        options: [
          ["40/30", "표준 40% / 10% 하락 시 30%"],
          ["35/25", "조건부 35% / 10% 하락 시 25%"],
          ["custom", "직접 검토"],
        ],
      }),
    ],
    acceptance: [
      "공급처 원문 단가·MOQ·배송비가 확인됨",
      "동일상품·동일 묶음의 판매 근거 현재가가 검증됨",
      "통과 후보 5개 이상 또는 명확한 차단 사유가 보고됨",
    ],
  },
  {
    id: "handoff",
    step: "02",
    title: "상품·가격 선택",
    shortTitle: "선택 승인",
    summary: "한 후보와 판매가를 명시적으로 선택해 프로젝트로 잠급니다.",
    availability: "partial",
    skill: "coupang-commerce-orchestrator",
    approvalGate: "이 상품과 판매가를 제가 직접 승인합니다.",
    inputs: [
      field("candidateId", "후보 ID", "text", { placeholder: "예: HDB-1" }),
      field("productName", "상품명", "text", { placeholder: "실제 판매할 상품" }),
      field("supplierUrl", "공급처 원문 URL", "url", { placeholder: "https://..." }),
      field("approvedPrice", "승인 판매가", "number", { placeholder: "9900", suffix: "원" }),
    ],
    acceptance: ["상품과 묶음 수량이 하나로 고정됨", "가격 시나리오와 근거 URL이 보존됨", "사용자 승인 기록이 남음"],
  },
  {
    id: "product-planning",
    step: "03",
    title: "상품기획",
    shortTitle: "상품기획",
    summary: "실제 SKU 사실과 고객 불만을 판매 가능한 소구로 정리합니다.",
    availability: "ready",
    skill: "coupang-product-planning",
    approvalGate: "현재 상품기획 버전을 제가 직접 승인합니다.",
    inputs: [
      field("identityAssets", "실제 SKU 사진·파일 경로", "textarea", { placeholder: "정면·후면·측면·라벨 경로 또는 URL" }),
      field("measurements", "실측·라벨 정보", "textarea", { placeholder: "사이즈, 구성, 소재, 관리법" }),
      field("lowRatingReviews", "경쟁사 저평점 리뷰 근거", "textarea", { placeholder: "별점 1~3점 리뷰 URL 또는 조사 파일" }),
    ],
    acceptance: ["제품 사실과 미검증 가설이 분리됨", "저평점 불만과 해결 가능성이 연결됨", "phase_1·phase_2 계획이 구분됨"],
  },
  {
    id: "content-planning",
    step: "04",
    title: "콘텐츠기획",
    shortTitle: "콘텐츠기획",
    summary: "주장·근거·장면을 상세페이지의 구매 서사로 바꿉니다.",
    availability: "ready",
    skill: "coupang-content-studio",
    approvalGate: "현재 콘텐츠기획 버전을 제가 직접 승인합니다.",
    inputs: [
      field("productPlan", "승인된 상품기획 경로", "text", { placeholder: "20-product-planning/product-plan.json" }),
      field("coreClaims", "핵심 소구", "textarea", { placeholder: "확정 주장만 입력" }),
      field("requiredScenes", "반드시 필요한 장면", "textarea", { placeholder: "제품 단독, 사용 장면, 치수, 비교 등" }),
    ],
    acceptance: ["모듈마다 주장·근거·자산 ID가 있음", "필수 장면과 금지 요소가 명시됨", "수치형 QA 기준이 잠김"],
  },
  {
    id: "detail-page",
    step: "05",
    title: "상세페이지 제작",
    shortTitle: "상세페이지",
    summary: "승인된 기획과 실제 자산으로 이미지·HTML을 조립합니다.",
    availability: "partial",
    skill: "coupang-detail-page-generator",
    inputs: [
      field("contentPlan", "승인된 콘텐츠기획 경로", "text", { placeholder: "30-content-planning/content-plan.json" }),
      field("sourceAssets", "실제 제품 자산 폴더", "text", { placeholder: "40-assets/source" }),
      field("identityStatus", "제품 동일성 상태", "select", {
        options: [["verified", "실제 SKU 확인 완료"], ["concept-only", "연출 프리뷰 전용"], ["blocked", "확인 대기"]],
      }),
    ],
    acceptance: ["실제 SKU와 생성 자산의 계보가 분리됨", "소재별 자동·육안 QA가 기록됨", "360px·800px 통합 QA가 통과함"],
  },
  {
    id: "motion",
    step: "06",
    title: "GIF·짧은 영상",
    shortTitle: "모션",
    summary: "한 동작이나 효용을 실촬영 또는 허용 자산으로 증명합니다.",
    availability: "planned",
    skill: "coupang-content-studio",
    inputs: [
      field("motionGoal", "증명할 한 가지 효용", "text", { placeholder: "예: 착용 범위 변화" }),
      field("motionAssets", "촬영·프레임 자산 경로", "text", { placeholder: "40-assets/motion" }),
    ],
    acceptance: ["3~6초 안에 하나의 효용만 보여줌", "정적 대체 이미지가 있음", "감소된 모션 설정에 대응함"],
  },
  {
    id: "html",
    step: "07",
    title: "채널 HTML·패키지",
    shortTitle: "HTML",
    summary: "편집 가능한 정본과 쿠팡용 정적 결과를 분리합니다.",
    availability: "planned",
    skill: "coupang-detail-page-generator",
    inputs: [
      field("htmlSource", "편집 가능한 HTML 정본", "text", { placeholder: "50-detail-page/html/detail-page.html" }),
      field("channel", "판매 채널", "select", { options: [["coupang", "쿠팡"], ["smartstore", "스마트스토어"], ["other", "기타 오픈마켓"]] }),
      field("staticFallback", "정적 대체 패키지", "text", { placeholder: "50-detail-page/channel-packages" }),
    ],
    acceptance: ["카피가 이미지가 아닌 HTML로 편집 가능함", "채널별 허용 형식과 대체안이 구분됨", "링크·파일 용량이 검증됨"],
  },
  {
    id: "publish-qa",
    step: "08",
    title: "게시 전 QA",
    shortTitle: "게시 QA",
    summary: "순서·크롭·카피·접근성·광고 표현을 최종 점검합니다.",
    availability: "partial",
    skill: "coupang-publish-qa",
    approvalGate: "QA 결과를 확인했고 게시 여부를 제가 직접 결정합니다.",
    inputs: [
      field("packagePath", "검수할 패키지 경로", "text", { placeholder: "50-detail-page/channel-packages/coupang" }),
      field("evidenceLedger", "주장·근거 원장 경로", "text", { placeholder: "60-qa/evidence-ledger.json" }),
      field("viewports", "검수 화면 폭", "select", { options: [["360,800", "모바일 360px + 데스크톱 800px"], ["360", "모바일 360px"], ["800", "데스크톱 800px"]] }),
    ],
    acceptance: ["모듈 순서와 주장-이미지 연결이 일치함", "잘림·오버플로·고아행 오류가 0건임", "근거 없는 광고 표현이 0건임"],
  },
  {
    id: "feedback",
    step: "09",
    title: "판매 피드백",
    shortTitle: "피드백",
    summary: "판매·광고·반품 신호를 다음 검증과 개선으로 연결합니다.",
    availability: "planned",
    skill: "coupang-commerce-orchestrator",
    inputs: [
      field("period", "측정 기간", "text", { placeholder: "예: 2026-08-01 ~ 2026-08-14" }),
      field("unitsSold", "판매 수량", "number", { placeholder: "2", suffix: "개" }),
      field("adSpend", "광고비", "number", { placeholder: "10000", suffix: "원" }),
      field("attributedRevenue", "광고 귀속 매출", "number", { placeholder: "40000", suffix: "원" }),
    ],
    acceptance: ["기간과 캠페인 ID가 분리 기록됨", "판매 2개 이상·ROAS 400% 이상을 AND로 판정함", "검증된 학습만 다음 기획에 반영함"],
  },
];

export function createInitialState(now = new Date().toISOString()) {
  return {
    schemaVersion: SCHEMA_VERSION,
    project: {
      id: "local-draft",
      name: "새 프로젝트",
      channel: "coupang",
      sourcingMode: "high-markup",
      status: "active",
      createdAt: now,
      updatedAt: now,
    },
    workflow: { currentStage: "sourcing", completedStages: [], blockedReason: null },
    stageData: Object.fromEntries(
      STAGES.map((stage) => [stage.id, { inputs: {}, completed: false, approved: false }]),
    ),
    folderMap: {},
    links: { reportRuns: [], legacyDetailPageProjects: [] },
  };
}

function valuePresent(value, input) {
  if (input.type === "number") return value !== "" && value !== null && Number.isFinite(Number(value));
  return typeof value === "string" ? value.trim().length > 0 : value !== undefined && value !== null;
}

export function getStage(stageId) {
  const stage = STAGES.find((item) => item.id === stageId);
  if (!stage) throw new Error(`알 수 없는 단계: ${stageId}`);
  return stage;
}

export function missingInputs(state, stageId) {
  const stage = getStage(stageId);
  const inputs = state.stageData?.[stageId]?.inputs ?? {};
  return stage.inputs.filter((input) => input.required && !valuePresent(inputs[input.id], input));
}

export function deriveProgress(state) {
  let previousComplete = true;
  let currentStageId = null;
  const stages = STAGES.map((stage) => {
    const record = state.stageData?.[stage.id] ?? { inputs: {}, completed: false, approved: false };
    const missing = missingInputs(state, stage.id);
    const approvalReady = !stage.approvalGate || record.approved === true;
    const complete = previousComplete && record.completed === true && missing.length === 0 && approvalReady;
    let status = "locked";
    if (complete) status = "completed";
    else if (previousComplete && currentStageId === null) {
      status = "current";
      currentStageId = stage.id;
    }
    previousComplete = previousComplete && complete;
    return { ...stage, status, missing, approvalReady, complete };
  });
  const completedCount = stages.filter((stage) => stage.complete).length;
  return {
    stages,
    completedCount,
    currentStageId,
    percentage: Math.round((completedCount / STAGES.length) * 100),
  };
}

function touch(state, now) {
  return {
    ...state,
    project: { ...state.project, updatedAt: now ?? new Date().toISOString() },
  };
}

export function updateStageInput(state, stageId, fieldId, value, now) {
  getStage(stageId);
  const record = state.stageData[stageId] ?? { inputs: {}, completed: false, approved: false };
  return touch(
    {
      ...state,
      stageData: {
        ...state.stageData,
        [stageId]: { ...record, inputs: { ...record.inputs, [fieldId]: value } },
      },
    },
    now,
  );
}

export function setStageApproval(state, stageId, approved, now) {
  getStage(stageId);
  const record = state.stageData[stageId];
  return touch(
    { ...state, stageData: { ...state.stageData, [stageId]: { ...record, approved: Boolean(approved) } } },
    now,
  );
}

export function selectSourcingCandidate(state, candidate, approvedPrice, now) {
  if (!candidate?.selectable || candidate.sourceDecision !== "SHORTLIST") {
    throw new Error("전체 소싱 검증을 통과한 SHORTLIST 후보만 선택할 수 있습니다.");
  }
  const record = state.stageData?.handoff;
  if (!record) throw new Error("상품·가격 선택 단계가 없습니다.");
  const price = approvedPrice ?? candidate.recommendedPrice ?? "";
  return touch({
    ...state,
    stageData: {
      ...state.stageData,
      handoff: {
        ...record,
        inputs: {
          ...record.inputs,
          candidateId: candidate.candidateId,
          productName: candidate.productName,
          supplierUrl: candidate.supplierUrl,
          approvedPrice: price === "" ? "" : String(price),
        },
        approved: false,
        completed: false,
        selection: {
          candidateId: candidate.candidateId,
          productName: candidate.productName,
          supplierUrl: candidate.supplierUrl,
          sourceDecision: candidate.sourceDecision,
          reportPath: candidate.reportPath,
          unitSupplyPrice: candidate.unitSupplyPrice ?? null,
          recommendedPrice: candidate.recommendedPrice ?? null,
          marketPriceMin: candidate.marketPriceMin ?? null,
          marketPriceMax: candidate.marketPriceMax ?? null,
          marginLow: candidate.marginLow ?? null,
          marginHigh: candidate.marginHigh ?? null,
          selectable: true,
          selectedAt: now ?? new Date().toISOString(),
        },
      },
    },
  }, now);
}

export function confirmSourcingSelection(state, now) {
  const record = state.stageData?.handoff;
  const selection = record?.selection;
  if (deriveProgress(state).currentStageId !== "handoff") {
    throw new Error("현재 상품·가격 선택 단계가 아닙니다.");
  }
  if (!selection?.selectable || selection.sourceDecision !== "SHORTLIST") {
    throw new Error("전체 소싱 검증을 통과한 SHORTLIST 후보를 먼저 선택해 주세요.");
  }
  if (record.inputs?.candidateId !== selection.candidateId) {
    throw new Error("선택한 후보와 저장된 후보 ID가 일치하지 않습니다.");
  }
  const approvedPrice = numberOrNull(record.inputs?.approvedPrice);
  if (approvedPrice === null || approvedPrice <= 0) {
    throw new Error("승인 판매가는 0보다 큰 숫자여야 합니다.");
  }
  const timestamp = now ?? new Date().toISOString();
  const confirmed = touch({
    ...state,
    stageData: {
      ...state.stageData,
      handoff: {
        ...record,
        selection: { ...selection, approvedPrice, confirmedAt: timestamp },
      },
    },
  }, timestamp);
  const approved = setStageApproval(confirmed, "handoff", true, timestamp);
  return setStageCompleted(approved, "handoff", true, timestamp);
}

export function canCompleteStage(state, stageId) {
  const stage = getStage(stageId);
  const progressStage = deriveProgress(state).stages.find((item) => item.id === stageId);
  const record = state.stageData[stageId];
  return progressStage?.status === "current" && missingInputs(state, stageId).length === 0 && (!stage.approvalGate || record.approved);
}

export function setStageCompleted(state, stageId, completed, now) {
  getStage(stageId);
  if (completed && !canCompleteStage(state, stageId)) return state;
  const record = state.stageData[stageId];
  const next = touch(
    { ...state, stageData: { ...state.stageData, [stageId]: { ...record, completed: Boolean(completed) } } },
    now,
  );
  return withDerivedWorkflow(next);
}

export function withDerivedWorkflow(state) {
  const progress = deriveProgress(state);
  return {
    ...state,
    workflow: {
      ...state.workflow,
      currentStage: progress.currentStageId ?? "feedback",
      completedStages: progress.stages.filter((stage) => stage.complete).map((stage) => stage.id),
    },
  };
}

function specialistFor(_state, stage) {
  if (stage.id === "sourcing") return "coupang-best-high-markup-sourcing";
  return stage.skill;
}

export function buildCodexPrompt(state, stageId) {
  const stage = getStage(stageId);
  const record = state.stageData[stageId];
  const specialist = specialistFor(state, stage);
  const knownInputLines = stage.inputs
    .filter((input) => valuePresent(record.inputs[input.id], input))
    .map((input) => `- ${input.label}: ${record.inputs[input.id]}`);
  if (stage.id === "sourcing" && !valuePresent(record.inputs.category, stage.inputs.find((input) => input.id === "category"))) {
    knownInputLines.unshift(
      `- 찾고 싶은 카테고리: 미지정 (도매꾹 Best 전체·6개 대분류 균등 탐색: ${DOMEGGOOK_BEST_CATEGORIES.join(", ")})`,
    );
  }
  const knownInputs = knownInputLines.join("\n");
  const missing = missingInputs(state, stageId).map((input) => input.label).join(", ") || "없음";
  const sourcingExecution = stage.id === "sourcing" ? [
    "",
    "소싱 실행 요구:",
    "- 설명만 하지 말고 실제 조사를 실행해 제품 후보 또는 검증 차단 결과를 만든다.",
    "- 날짜 규칙에 맞는 HTML·JSON 보고서를 생성하고 최종 응답에 절대 경로를 남긴다.",
    "- 완전 동일 1개 상품의 판매 근거 현재가 최저~최고와 수익률 최저~최고를 쿠팡 URL과 함께 비교한다.",
    "- 고가라도 리뷰·최근 구매 근거가 있으면 가격 수용성 상단 기준으로 보존하고, 판매 근거 없는 고가는 제외한다.",
    "- 생성한 보고서 상대 경로를 project.json의 links.reportRuns에 등록한다.",
    "- 접근 차단 시 값을 꾸미지 말고 실제 조사한 후보와 차단 사유·재개 지점을 같은 보고서에 남긴다.",
  ] : [];
  return [
    `Use $coupang-commerce-automation:${specialist} to handle the next step.`,
    "",
    `프로젝트: ${state.project.name} (${state.project.id})`,
    `현재 단계: ${stage.step} ${stage.title}`,
    "",
    "확인된 입력:",
    knownInputs || "- 아직 입력 없음",
    `미입력 필수 항목: ${missing}`,
    `사용자 승인: ${record.approved ? "승인함" : "미승인"}`,
    ...sourcingExecution,
    "",
    "앞 단계의 근거와 승인 게이트를 다시 확인하고 다음 한 단계만 진행해줘. 공급처 연락·발주·결제, 상품 등록, 광고 집행은 하지 마.",
  ].join("\n");
}

export function validateImportedState(payload) {
  if (!payload || payload.schemaVersion !== SCHEMA_VERSION || typeof payload.project !== "object") {
    throw new Error("지원하지 않는 상태 파일입니다.");
  }
  if (setEquals(Object.keys(payload.stageData ?? {}), STAGES.map((stage) => stage.id)) === false) {
    throw new Error("지원하지 않는 상태 파일입니다.");
  }
  return JSON.parse(JSON.stringify(payload));
}

function setEquals(left, right) {
  const a = new Set(left);
  const b = new Set(right);
  return a.size === b.size && [...a].every((value) => b.has(value));
}
