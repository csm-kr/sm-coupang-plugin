import { useEffect, useMemo, useRef, useState } from "react";
import {
  PROJECT_ID_PATTERN,
  STAGES,
  actualDomeggookSamples,
  actualSourcingPairs,
  buildCodexPrompt,
  canCompleteStage,
  confirmSourcingSelection,
  createDefaultProjectId,
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
  sourcingReportMatchesRun,
  sourcingResultState,
  stageActionCopy,
  setPriorStageConfirmation,
  setStageApproval,
  setStageCompleted,
  updateStageInput,
  withDerivedWorkflow,
} from "./workflow.js";

const AVAILABILITY = {
  ready: ["사용 가능", "ready"],
  partial: ["부분 지원", "partial"],
  planned: ["계획 단계", "planned"],
};

const RUN_STATUS = {
  queued: ["실행 준비", "queued"],
  running: ["실행 중", "running"],
  stopping: ["중지 중", "stopping"],
  succeeded: ["완료", "succeeded"],
  failed: ["실패", "failed"],
  stopped: ["중지됨", "stopped"],
};

async function api(path, options = {}) {
  const response = await fetch(path, {
    ...options,
    headers: { "Content-Type": "application/json", ...(options.headers ?? {}) },
  });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(payload.error || `요청 실패 (${response.status})`);
  return payload;
}

function stageById(stageId) {
  return STAGES.find((stage) => stage.id === stageId) ?? STAGES[0];
}

function formatDate(value) {
  if (!value) return "기록 없음";
  return new Intl.DateTimeFormat("ko-KR", { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" }).format(new Date(value));
}

const CANDIDATE_DECISIONS = {
  SHORTLIST: ["선택 가능", "selectable", "전체 소싱 검증을 통과했습니다."],
  CONDITIONAL_TEST_PRICE_REVIEW: ["조건부 검토", "conditional", "실물·권리·가격 수용성 확인이 더 필요합니다."],
  HIGH_MARKUP_DISCOVERY: ["고배수 pair 발견", "discovery", "판매 근거가 있는 고배수 pair이며 SHORTLIST 재검증 전입니다."],
  PRICE_REVIEW_BLOCKED: ["추가 조사 필요", "blocked", "가격·동일성 또는 공급조건 근거가 부족합니다."],
  FILTERED_OUT: ["기준 미달", "rejected", "탐색 기준을 충족하지 못했습니다."],
  REJECT: ["제외", "rejected", "전체 소싱 검증에서 제외됐습니다."],
};

function candidateDecision(candidate) {
  return CANDIDATE_DECISIONS[candidate.sourceDecision]
    ?? [candidate.sourceDecision || "판정 대기", "blocked", "판정 근거를 확인해 주세요."];
}

function CreateProjectDialog({ onClose, onCreated }) {
  const [form, setForm] = useState(() => ({
    projectId: createDefaultProjectId(),
    name: "",
    channel: "coupang",
    sourcingMode: "high-markup",
  }));
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const valid = PROJECT_ID_PATTERN.test(form.projectId) && form.name.trim();

  async function submit(event) {
    event.preventDefault();
    if (!valid) return;
    setSubmitting(true);
    setError("");
    try {
      const created = await api("/api/projects", { method: "POST", body: JSON.stringify(form) });
      onCreated(created);
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="dialog-backdrop" role="presentation" onMouseDown={(event) => event.target === event.currentTarget && onClose()}>
      <section className="dialog" role="dialog" aria-modal="true" aria-labelledby="create-title">
        <button className="icon-button dialog-close" type="button" onClick={onClose} aria-label="닫기">×</button>
        <p className="eyebrow">새 작업 공간</p>
        <h2 id="create-title">프로젝트를 시작할게요</h2>
        <p className="dialog-copy">상품 하나마다 폴더와 진행 상태를 따로 만듭니다. 나중에 이름은 바꿀 수 있지만 프로젝트 ID는 경로가 되므로 고정됩니다.</p>
        <form onSubmit={submit} className="create-form">
          <label>
            <span>프로젝트 이름</span>
            <input autoFocus value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} placeholder="예: 여름 스포츠 마스크" />
          </label>
          <label>
            <span>프로젝트 ID</span>
            <input value={form.projectId} onChange={(event) => setForm({ ...form, projectId: event.target.value.toLowerCase().replace(/[^a-z0-9-]/g, "-") })} placeholder="summer-mask-001" />
            <small>자동으로 만들었습니다. 필요할 때만 소문자 영문·숫자·하이픈으로 수정하세요.</small>
          </label>
          <div className="form-columns">
            <label>
              <span>판매 채널</span>
              <select value={form.channel} onChange={(event) => setForm({ ...form, channel: event.target.value })}>
                <option value="coupang">쿠팡</option>
                <option value="smartstore">스마트스토어</option>
                <option value="other">기타 오픈마켓</option>
              </select>
            </label>
            <label>
              <span>탐색 기준</span>
              <input value="도매꾹 Best 고배수 pair 탐색" readOnly />
            </label>
          </div>
          {error && <p className="form-error">{error}</p>}
          <button className="primary-button wide" type="submit" disabled={!valid || submitting}>{submitting ? "만드는 중…" : "프로젝트 폴더 만들기"}</button>
        </form>
      </section>
    </div>
  );
}

function ProjectRail({ projects, activeId, onSelect, onCreate }) {
  return (
    <aside className="project-rail">
      <div className="rail-heading">
        <div>
          <p className="eyebrow">WORKSPACE</p>
          <h2>내 프로젝트</h2>
        </div>
        <button className="add-project" type="button" onClick={onCreate} aria-label="새 프로젝트">＋</button>
      </div>
      <div className="project-list">
        {projects.length === 0 && <p className="empty-note">아직 프로젝트가 없습니다.</p>}
        {projects.map((project) => {
          const stage = stageById(project.currentStage);
          return (
            <button key={project.projectId} className={`project-card ${activeId === project.projectId ? "active" : ""}`} type="button" onClick={() => onSelect(project.projectId)}>
              <span className="project-card-top"><strong>{project.name}</strong><i>{stage.step}</i></span>
              <span className="project-id">{project.projectId}</span>
              <span className="project-meta"><b>{stage.shortTitle}</b><time>{formatDate(project.updatedAt)}</time></span>
              {project.blockedReason && <span className="blocked-chip">확인 필요</span>}
            </button>
          );
        })}
      </div>
      <div className="rail-footnote">
        <span className="privacy-dot" />
        <p><strong>프로젝트 상태는 로컬 저장</strong><br />실행 시 입력과 필요한 파일은 Codex 설정에 따라 처리됩니다.</p>
      </div>
    </aside>
  );
}

function StageRail({ progress, selectedId, onSelect }) {
  return (
    <nav className="stage-rail" aria-label="전체 워크플로 진행률">
      {progress.stages.map((stage) => (
        <button
          key={stage.id}
          type="button"
          onClick={() => onSelect(stage.id)}
          aria-current={selectedId === stage.id ? "step" : undefined}
          className={`stage-item ${stage.status} ${selectedId === stage.id ? "selected" : ""}`}
        >
          <span className="stage-number">{stage.complete ? "✓" : stage.step}</span>
          <span><strong>{stage.shortTitle}</strong><small>{stage.status === "locked" ? "앞 단계 대기" : stage.status === "confirmed" ? "사용자 완료 확인" : AVAILABILITY[stage.availability][0]}</small></span>
        </button>
      ))}
    </nav>
  );
}

function FlowSummary({ stage, run, runtime, starting, onStart }) {
  const copy = stageActionCopy(stage, run);
  const canRun = ["run", "rerun"].includes(copy.action);
  const canJump = ["monitor", "select"].includes(copy.action);

  function activate() {
    if (canRun) {
      onStart();
      return;
    }
    const targetId = copy.action === "select" ? "candidate-decision-title" : "codex-console-title";
    document.getElementById(targetId)?.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  return (
    <section className={`flow-summary ${copy.action}`} aria-live="polite">
      <span className="flow-summary-step" aria-hidden="true">{stage.complete ? "✓" : stage.step}</span>
      <div className="flow-summary-copy">
        <p>지금 할 일</p>
        <strong>{copy.label}</strong>
        <small>{copy.helper}</small>
      </div>
      {(canRun || canJump) && (
        <button
          className={canRun ? "primary-button flow-summary-button" : "ghost-button flow-summary-button"}
          type="button"
          onClick={activate}
          disabled={canRun && (!runtime?.codexAvailable || starting)}
        >
          {starting ? "시작 중…" : copy.action === "monitor" ? "실행 로그 보기" : copy.action === "select" ? "후보 비교하기" : copy.label}
        </button>
      )}
      {copy.action === "locked" && <span className="flow-summary-locked">잠김</span>}
      {copy.action === "confirmed" && <span className="flow-summary-confirmed">완료 확인</span>}
    </section>
  );
}

function FormField({ input, value, disabled, onChange }) {
  const id = `field-${input.id}`;
  const control = input.type === "textarea" ? (
    <textarea id={id} rows="3" value={value ?? ""} disabled={disabled} placeholder={input.placeholder} onChange={(event) => onChange(event.target.value)} />
  ) : input.type === "select" ? (
    <select id={id} value={value ?? ""} disabled={disabled} onChange={(event) => onChange(event.target.value)}>
      <option value="">선택해 주세요</option>
      {input.options.map(([optionValue, label]) => <option key={optionValue} value={optionValue}>{label}</option>)}
    </select>
  ) : (
    <div className="input-with-suffix">
      <input id={id} type={input.type} min={input.min} step={input.step} value={value ?? ""} disabled={disabled} placeholder={input.placeholder} onChange={(event) => onChange(event.target.value)} />
      {input.suffix && <span>{input.suffix}</span>}
    </div>
  );
  return <label className="field-label" htmlFor={id}><span>{input.label}<b>{input.required ? "필수" : "선택"}</b></span>{control}</label>;
}

function SourcingResultPanel({ project, run, onContinue }) {
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const reportKey = (project.links?.reportRuns ?? []).join("|");
  const runReportKey = (run?.artifacts ?? []).join("|");
  const state = sourcingResultState(run);

  useEffect(() => {
    let cancelled = false;
    async function loadResult() {
      if (!["completed", "failed"].includes(state.mode)) return;
      setLoading(true);
      setError("");
      const reportPaths = state.mode === "failed" && (run?.artifacts ?? []).length > 0
        ? run.artifacts
        : project.links?.reportRuns;
      const hrefs = sourcingReportJsonHrefs(reportPaths);
      const settled = await Promise.allSettled(hrefs.map(async (href) => (
        normalizeSourcingReport(await api(href), href)
      )));
      const reports = settled
        .filter((result) => result.status === "fulfilled")
        .map((result) => result.value);
      const loaded = state.mode === "failed"
        ? reports.find((item) => sourcingReportMatchesRun(item, run))
        : reports.find((item) => item.status !== "UNKNOWN" || item.candidates.length > 0);
      if (!cancelled) {
        setReport(loaded ?? null);
        setError(loaded ? "" : "이번 실행의 소싱 보고서를 읽지 못했습니다.");
        setLoading(false);
      }
    }
    loadResult().catch((loadError) => {
      if (!cancelled) {
        setError(loadError.message);
        setLoading(false);
      }
    });
    return () => { cancelled = true; };
  }, [project.project.id, reportKey, runReportKey, run?.startedAt, state.mode]);

  if (state.mode === "running") {
    return <section className="sourcing-result-state running" aria-live="polite"><strong>진행중입니다.</strong></section>;
  }
  if (!["completed", "failed"].includes(state.mode)) {
    return <section className={`sourcing-result-state ${state.mode}`} aria-live="polite"><strong>{state.message}</strong></section>;
  }
  if (loading) {
    return <section className="sourcing-result-state loading" aria-live="polite"><strong>실제 결과를 불러오는 중입니다.</strong></section>;
  }

  const pairs = actualSourcingPairs(report);
  const samples = actualDomeggookSamples(report);
  const artifactPath = (run?.artifacts ?? []).find((path) => path.endsWith(".html"))
    ?? report?.reportPath?.replace(/\.json$/i, ".html")
    ?? "";
  const artifactHref = reportHref(artifactPath);
  const selectableCount = pairs.filter((pair) => pair.selectable).length;

  if (state.mode === "failed" || pairs.length === 0) {
    const runFailed = state.mode === "failed";
    const failureMessage = runFailed
      ? state.message
      : report?.failureReason || error || "설정 조건을 충족한 pair가 확인되지 않았습니다.";
    return (
      <section className="sourcing-failure" aria-labelledby="sourcing-failure-title">
        <div className="sourcing-results-head">
          <div><p className="eyebrow">{runFailed ? "FAILED" : "BLOCKED"}</p><h3 id="sourcing-failure-title">{runFailed ? "소싱 실패" : "소싱 검증 미완료"}</h3></div>
          <span><strong>{samples.length}개</strong> 샘플 기록</span>
        </div>
        <div className="sourcing-failure-reason"><small>실패 이유</small><strong>{failureMessage}</strong></div>
        <div className="sourcing-samples">
          <h4>도매꾹 확인 샘플</h4>
          {samples.length > 0 ? (
            <ul>{samples.map((sample) => (
              <li key={`${sample.reportPath}:${sample.candidateId || sample.supplierUrl}`}>
                <a href={sample.supplierUrl} target="_blank" rel="noreferrer">{sample.productName || sample.candidateId}</a>
                <span>{[sample.category, sample.rank ? `${sample.rank}위` : "", formatOptionalWon(sample.unitSupplyPrice)].filter(Boolean).join(" · ")}</span>
              </li>
            ))}</ul>
          ) : <p>{error || "이번 실행에서 기록된 도매꾹 샘플이 없습니다."}</p>}
        </div>
        {artifactHref && <div className="sourcing-result-actions"><a className="ghost-button" href={artifactHref} target="_blank" rel="noreferrer">{runFailed ? "실패 보고서 보기" : "조사 보고서 보기"}</a></div>}
      </section>
    );
  }

  return (
    <section className="sourcing-results" aria-labelledby="sourcing-results-title">
      <div className="sourcing-results-head">
        <div><p className="eyebrow">RESULT</p><h3 id="sourcing-results-title">실제 결과</h3></div>
        <span><strong>{pairs.length}개</strong> pair 발견</span>
      </div>
      <div className="sourcing-result-grid">
        {pairs.map((pair) => (
            <article className="sourcing-result-card" key={`${pair.reportPath}:${pair.candidateId}`}>
              <div>
                <small>도매꾹</small>
                <a href={pair.supplierUrl} target="_blank" rel="noreferrer">{pair.productName || "도매꾹 상품"}</a>
                <strong>{formatOptionalWon(pair.unitSupplyPrice)}</strong>
              </div>
              <span aria-hidden="true">↔</span>
              <div>
                <small>쿠팡</small>
                <a href={pair.coupangUrl} target="_blank" rel="noreferrer">{pair.coupangProductName || "쿠팡 판매 상품"}</a>
                <strong>{formatOptionalWon(pair.currentSalePrice)}</strong>
              </div>
              <footer>
                <b>{formatOptionalMultiple(pair.markupMultiple)}</b>
                {pair.salesEvidenceLabel && <em>{pair.salesEvidenceLabel}</em>}
              </footer>
            </article>
        ))}
      </div>
      <div className="sourcing-result-actions">
        {artifactHref && <a className="ghost-button" href={artifactHref} target="_blank" rel="noreferrer">실제 보고서 보기</a>}
        {selectableCount > 0 && <button className="complete-button" type="button" onClick={onContinue}>상품 선택으로 이동</button>}
      </div>
    </section>
  );
}

function CandidateDecisionPanel({ project, disabled, onSelect, onPriceChange, onConfirm, onReturnToSourcing }) {
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [activeCandidateId, setActiveCandidateId] = useState(project.stageData.handoff.selection?.candidateId ?? "");
  const reportKey = (project.links?.reportRuns ?? []).join("|");
  const selectedId = project.stageData.handoff.inputs?.candidateId ?? "";
  const approvedPrice = project.stageData.handoff.inputs?.approvedPrice ?? "";

  useEffect(() => {
    let cancelled = false;
    async function loadCandidates() {
      setLoading(true);
      setError("");
      const hrefs = sourcingReportJsonHrefs(project.links?.reportRuns);
      if (hrefs.length === 0) {
        if (!cancelled) {
          setReport(null);
          setLoading(false);
        }
        return;
      }
      const settled = await Promise.allSettled(hrefs.map(async (href) => {
        const payload = await api(href);
        return normalizeSourcingReport(payload, href);
      }));
      const loaded = settled
        .filter((result) => result.status === "fulfilled")
        .map((result) => result.value)
        .find((item) => item.candidates.length > 0);
      if (!cancelled) {
        setReport(loaded ?? null);
        setError(loaded ? "" : "연결된 소싱 JSON에서 후보 데이터를 읽지 못했습니다.");
        setLoading(false);
      }
    }
    loadCandidates().catch((loadError) => {
      if (!cancelled) {
        setError(loadError.message);
        setLoading(false);
      }
    });
    return () => { cancelled = true; };
  }, [project.project.id, reportKey]);

  useEffect(() => {
    if (selectedId) setActiveCandidateId(selectedId);
    else if (!activeCandidateId && report?.candidates[0]) setActiveCandidateId(report.candidates[0].candidateId);
  }, [selectedId, report]);

  if (loading) {
    return <div className="candidate-loading"><div className="loader" /><p>소싱 결과를 후보 카드로 정리하고 있습니다…</p></div>;
  }

  if (!report) {
    return (
      <div className="candidate-empty">
        <strong>UI에서 판단할 소싱 후보가 아직 없습니다.</strong>
        <p>{error || "소싱 실행이 끝나 후보 JSON이 프로젝트에 연결되면 이곳에 자동으로 표시됩니다."}</p>
        <button className="ghost-button" type="button" onClick={onReturnToSourcing}>소싱 단계 확인하기</button>
      </div>
    );
  }

  const selectableCount = report.candidates.filter((candidate) => candidate.selectable).length;
  const active = report.candidates.find((candidate) => candidate.candidateId === activeCandidateId)
    ?? report.candidates[0];
  const selected = report.candidates.find((candidate) => candidate.candidateId === selectedId);
  const activeDecision = candidateDecision(active);
  const canConfirm = Boolean(selected?.selectable && Number(approvedPrice) > 0 && !disabled);

  return (
    <section className="candidate-decision" aria-labelledby="candidate-decision-title">
      <div className="candidate-decision-head">
        <div>
          <h3 id="candidate-decision-title">도매꾹 ↔ 쿠팡 pair를 비교하세요</h3>
          <p>설정 배수 이상인 판매 근거 pair가 핵심입니다. 낮은 가격의 다른 등록은 이 pair를 탈락시키지 않습니다.</p>
        </div>
        <span>{report.candidates.length}개 중 <strong>{selectableCount}개</strong> 선택 가능</span>
      </div>

      <div className="candidate-grid" role="list" aria-label="소싱 후보">
        {report.candidates.map((candidate) => {
          const decision = candidateDecision(candidate);
          const isActive = candidate.candidateId === active.candidateId;
          const isSelected = candidate.candidateId === selectedId;
          return (
            <button
              key={`${candidate.reportPath}:${candidate.candidateId}`}
              className={`candidate-card ${isActive ? "active" : ""} ${isSelected ? "selected" : ""}`}
              type="button"
              role="listitem"
              aria-pressed={isSelected}
              onClick={() => {
                setActiveCandidateId(candidate.candidateId);
                if (candidate.selectable && !disabled) onSelect(candidate);
              }}
            >
              <span className={`candidate-decision-chip ${decision[1]}`}>{decision[0]}</span>
              <small>{candidate.candidateId || "ID 확인 대기"}</small>
              <strong>{candidate.productName || "상품명 확인 대기"}</strong>
              <span className="candidate-card-metrics">
                <i><b>도매꾹 원가</b>{formatOptionalWon(candidate.unitSupplyPrice)}</i>
                <i><b>쿠팡 현재가</b>{formatOptionalWon(candidate.currentSalePrice)}</i>
                <i><b>가격 배수</b>{formatOptionalMultiple(candidate.markupMultiple)}</i>
              </span>
              <em>{isSelected ? "현재 선택" : candidate.selectable ? "클릭해 선택" : "클릭해 사유 확인"}</em>
            </button>
          );
        })}
      </div>

      <div className={`candidate-detail ${activeDecision[1]}`}>
        <div className="candidate-detail-title">
          <div><span className={`candidate-decision-chip ${activeDecision[1]}`}>{activeDecision[0]}</span><h4>{active.productName}</h4></div>
          <p>{activeDecision[2]}</p>
        </div>
        <dl className="candidate-facts">
          <div><dt>도매꾹 상품·개당 원가</dt><dd>{active.supplierUrl ? <a href={active.supplierUrl} target="_blank" rel="noreferrer">{active.productName}</a> : active.productName} · {formatOptionalWon(active.unitSupplyPrice)}</dd></div>
          <div><dt>쿠팡 판매 상품·현재가</dt><dd>{active.coupangUrl ? <a href={active.coupangUrl} target="_blank" rel="noreferrer">{active.coupangProductName || "쿠팡 상품"}</a> : (active.coupangProductName || "확인 대기")} · {formatOptionalWon(active.currentSalePrice)}</dd></div>
          <div><dt>가격 배수</dt><dd>{formatOptionalMultiple(active.markupMultiple)}</dd></div>
          <div><dt>판매 근거</dt><dd>{active.salesEvidenceLabel || "확인 대기"}</dd></div>
          <div><dt>공급 MOQ / 배송비</dt><dd>{active.minimumOrderQuantity ?? "확인 대기"}개 / {formatOptionalWon(active.wholesaleShippingTotal)}</dd></div>
          <div><dt>다음 검증 참고 수익률</dt><dd>{formatOptionalPercent(active.marginLow)} ~ {formatOptionalPercent(active.marginHigh)}</dd></div>
        </dl>
        {active.blockers.length > 0 && (
          <div className="candidate-blockers"><strong>다음 단계 전 확인할 점</strong><ul>{active.blockers.map((blocker) => <li key={blocker}>{blocker}</li>)}</ul></div>
        )}
      </div>

      {selectableCount === 0 ? (
        <div className="candidate-no-pass">
          <div><strong>지금은 다음 단계로 넘길 후보가 없습니다.</strong><p>차단 사유를 해결한 뒤 소싱을 다시 실행하면 이 화면이 자동 갱신됩니다.</p></div>
          <button className="ghost-button" type="button" onClick={onReturnToSourcing}>소싱으로 돌아가기</button>
        </div>
      ) : (
        <div className="candidate-confirm">
          <label>
            <span>최종 판매가 <b>필수</b></span>
            <div className="input-with-suffix"><input type="number" min="1" value={approvedPrice} disabled={!selected || disabled} onChange={(event) => onPriceChange(event.target.value)} placeholder="후보를 먼저 선택하세요" /><span>원</span></div>
          </label>
          <div>
            <p>{selected ? <><strong>{selected.productName}</strong>을 선택했습니다. 가격을 확인하면 바로 다음 단계로 이동합니다.</> : "선택 가능한 후보 카드를 클릭해 주세요."}</p>
            <button className="complete-button candidate-confirm-button" type="button" disabled={!canConfirm} onClick={onConfirm}>상품·가격 확정하고 상품기획으로</button>
          </div>
        </div>
      )}
    </section>
  );
}

function FolderMap({ project, legacy }) {
  const folders = Object.entries(project.folderMap ?? {});
  return (
    <section className="side-card folder-card">
      <div className="side-card-title"><p className="eyebrow">PROJECT MAP</p><h3>폴더는 이렇게 정리돼요</h3></div>
      <div className="folder-tree">
        <p className="folder-root"><span>▾</span> commerce-project/projects/<strong>{project.project.id}</strong></p>
        {folders.map(([key, path]) => <p key={key}><span>└</span><code>{path}</code></p>)}
      </div>
      <p className="folder-help">보고서는 복사하지 않고 아래 경로만 연결합니다.</p>
      <div className="report-links">
        {(project.links?.reportRuns ?? []).length === 0 ? <span>연결된 보고서 없음</span> : project.links.reportRuns.map((path) => {
          const href = reportHref(path);
          return href
            ? <a key={path} href={href} target="_blank" rel="noreferrer">{path}</a>
            : <code key={path}>{path}</code>;
        })}
      </div>
      {legacy.length > 0 && (
        <details className="legacy-list">
          <summary>기존 detail-page 작업 {legacy.length}개</summary>
          {legacy.map((item) => <p key={item.path}><strong>{item.name}</strong><code>{item.path}</code></p>)}
        </details>
      )}
    </section>
  );
}

function formatFileSize(bytes) {
  const value = Number(bytes);
  if (!Number.isFinite(value)) return "";
  if (value < 1024) return `${value} B`;
  if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} KB`;
  return `${(value / (1024 * 1024)).toFixed(1)} MB`;
}

function uploadContentType(file) {
  if (file.type) return file.type;
  const extension = file.name.split(".").pop()?.toLowerCase();
  return {
    gif: "image/gif",
    jpeg: "image/jpeg",
    jpg: "image/jpeg",
    png: "image/png",
    webp: "image/webp",
  }[extension] ?? "application/octet-stream";
}

function WorkspacePreview({ file, onClose }) {
  return (
    <div className="workspace-preview-backdrop" role="presentation" onMouseDown={(event) => event.target === event.currentTarget && onClose()}>
      <section className="workspace-preview" role="dialog" aria-modal="true" aria-labelledby="workspace-preview-title">
        <header>
          <div><p className="eyebrow">PROJECT PREVIEW</p><h2 id="workspace-preview-title">{file.name}</h2><code>{file.path}</code></div>
          <button className="icon-button" type="button" onClick={onClose} aria-label="미리보기 닫기">×</button>
        </header>
        <div className={`workspace-preview-canvas ${file.kind}`}>
          {file.kind === "image"
            ? <img src={file.href} alt={`${file.name} 프로젝트 자산 미리보기`} />
            : <iframe src={file.href} title={`${file.name} 미리보기`} sandbox="" />}
        </div>
      </section>
    </div>
  );
}

function WorkspaceViewer({ project, onToast, variant = "explorer", refreshKey = 0, onAssetsChanged }) {
  const [workspace, setWorkspace] = useState({ files: [], uploadTarget: "40-assets/source" });
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [dragging, setDragging] = useState(false);
  const [previewFile, setPreviewFile] = useState(null);
  const reportKey = (project.links?.reportRuns ?? []).join("|");

  async function loadFiles() {
    setLoading(true);
    try {
      const payload = await api(`/api/projects/${encodeURIComponent(project.project.id)}/workspace`);
      setWorkspace(payload);
    } catch (error) {
      onToast(`프로젝트 파일 확인 실패: ${error.message}`);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    setPreviewFile(null);
    loadFiles();
  }, [project.project.id, reportKey, refreshKey]);

  async function uploadFiles(fileList) {
    const files = [...fileList];
    if (files.length === 0) return;
    setUploading(true);
    const results = await Promise.allSettled(files.map(async (file) => {
      const response = await fetch(
        `/api/projects/${encodeURIComponent(project.project.id)}/assets?filename=${encodeURIComponent(file.name)}`,
        { method: "POST", headers: { "Content-Type": uploadContentType(file) }, body: file },
      );
      const payload = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(payload.error || `${file.name} 업로드 실패 (${response.status})`);
      return payload;
    }));
    const succeeded = results.filter((result) => result.status === "fulfilled");
    const failed = results.filter((result) => result.status === "rejected");
    if (succeeded.length > 0) {
      await loadFiles();
      onAssetsChanged?.();
      onToast(`${succeeded.length}개 이미지를 ${workspace.uploadTarget}에 저장했습니다.`);
    }
    if (failed.length > 0) onToast(failed[0].reason?.message || `${failed.length}개 이미지 업로드에 실패했습니다.`);
    setUploading(false);
    setDragging(false);
  }

  const sourceImages = workspace.files.filter((file) => (
    file.source === "project"
    && file.kind === "image"
    && (file.path === workspace.uploadTarget || file.path.startsWith(`${workspace.uploadTarget}/`))
  ));
  const visibleFiles = variant === "stage-assets" ? sourceImages : workspace.files;
  const groups = visibleFiles.reduce((result, file) => {
    const group = file.source === "report" ? "연결된 보고서" : file.path.includes("/") ? file.path.split("/", 1)[0] : "프로젝트 루트";
    if (!result[group]) result[group] = [];
    result[group].push(file);
    return result;
  }, {});

  return (
    <section className={`${variant === "stage-assets" ? "stage-asset-workspace" : "side-card"} workspace-viewer`}>
      <div className="side-card-title">
        <p className="eyebrow">{variant === "stage-assets" ? "PRODUCT ASSETS" : "PROJECT EXPLORER"}</p>
        <h3>{variant === "stage-assets" ? "이미지 드래그앤드롭과 미리보기" : "작업 파일과 미리보기"}</h3>
      </div>
      <p className="workspace-viewer-help">{variant === "stage-assets" ? "이미지 경로를 입력하지 마세요. 파일을 놓으면 원본 자산 폴더에 저장되고, 폴더 안 기존 이미지도 바로 미리볼 수 있습니다." : "HTML·이미지 미리보기와 JSON·텍스트 확인을 이 작업창 안에서 처리합니다."}</p>
      <label
        className={`asset-dropzone ${dragging ? "dragging" : ""} ${uploading ? "uploading" : ""}`}
        onDragEnter={(event) => { event.preventDefault(); setDragging(true); }}
        onDragOver={(event) => { event.preventDefault(); setDragging(true); }}
        onDragLeave={(event) => { event.preventDefault(); if (!event.currentTarget.contains(event.relatedTarget)) setDragging(false); }}
        onDrop={(event) => { event.preventDefault(); uploadFiles(event.dataTransfer.files); }}
      >
        <input type="file" accept=".png,.jpg,.jpeg,.gif,.webp" multiple disabled={uploading} onChange={(event) => { uploadFiles(event.target.files); event.target.value = ""; }} />
        <span>{uploading ? "저장 중…" : dragging ? "여기에 놓으세요" : "이미지를 끌어다 놓거나 클릭해 선택"}</span>
        <small>PNG·JPG·GIF·WEBP · 파일당 20MB 이하</small>
      </label>
      {variant === "stage-assets" ? (
        <div className="asset-preview-grid" aria-label="원본 자산 폴더 이미지 미리보기">
          {loading && <p className="empty-note">폴더 이미지를 불러오는 중…</p>}
          {!loading && sourceImages.length === 0 && <p className="empty-note">아직 이미지가 없습니다. 실제 SKU와 라벨 사진을 여기에 놓으세요.</p>}
          {!loading && sourceImages.map((file) => (
            <button key={`${file.source}:${file.path}`} type="button" onClick={() => setPreviewFile(file)} title={`${file.name} 크게 보기`}>
              <img src={file.href} alt={`${file.name} 자산 썸네일`} />
              <span><strong>{file.name}</strong><small>{formatFileSize(file.size)}</small></span>
            </button>
          ))}
        </div>
      ) : (
        <div className="workspace-file-tree" aria-label="프로젝트 파일">
          {loading && <p className="empty-note">파일을 불러오는 중…</p>}
          {!loading && workspace.files.length === 0 && <p className="empty-note">아직 프로젝트 파일이 없습니다.</p>}
          {!loading && Object.entries(groups).map(([group, files]) => (
            <details key={group} open>
              <summary><span>▾</span>{group}<small>{files.length}</small></summary>
              {files.map((file) => (
                <button key={`${file.source}:${file.path}`} type="button" disabled={!['html', 'image', 'json', 'text'].includes(file.kind)} onClick={() => setPreviewFile(file)} title={file.path}>
                  <i>{file.kind === "image" ? "▧" : file.kind === "html" ? "◇" : file.kind === "json" ? "{}" : "·"}</i>
                  <span><strong>{file.name}</strong><small>{formatFileSize(file.size)}</small></span>
                </button>
              ))}
            </details>
          ))}
        </div>
      )}
      {previewFile && <WorkspacePreview file={previewFile} onClose={() => setPreviewFile(null)} />}
    </section>
  );
}

function CodexConsole({ runtime, run, starting, onStart, onStop }) {
  const outputRef = useRef(null);
  const status = RUN_STATUS[run?.status] ?? ["대기", "idle"];
  useEffect(() => {
    if (outputRef.current) outputRef.current.scrollTop = outputRef.current.scrollHeight;
  }, [run?.events?.length]);

  return (
    <section className="codex-console" aria-labelledby="codex-console-title">
      <div className="console-head">
        <div>
          <p className="eyebrow">LIVE CODEX</p>
          <h3 id="codex-console-title">Codex 실행 콘솔</h3>
        </div>
        <span className={`run-status ${status[1]}`}><i />{status[0]}</span>
      </div>
      <div className="console-toolbar">
        <code>codex exec · {runtime?.sandbox || "workspace-write"}</code>
        {run?.threadId && <code>thread {run.threadId}</code>}
      </div>
      <div className="console-output" ref={outputRef} role="log" aria-live="polite" aria-label="Codex 실행 로그">
        {!runtime?.codexAvailable && <p className="console-error">Codex CLI를 찾을 수 없습니다. 설치와 로그인을 확인해 주세요.</p>}
        {runtime?.codexAvailable && !run && <p className="console-placeholder">아래 버튼을 누르면 현재 단계의 Codex 작업과 진행 로그가 여기에 표시됩니다.</p>}
        {(run?.events ?? []).map((event) => (
          <div className={`console-line event-${event.type?.replaceAll(".", "-") || "unknown"}`} key={`${event.sequence}-${event.receivedAt}`}>
            <time>{event.receivedAt?.slice(11, 19) || "--:--:--"}</time>
            <pre>{formatCodexEvent(event)}</pre>
          </div>
        ))}
        {run?.error && <p className="console-error">{run.error}</p>}
      </div>
      <div className="console-actions">
        <p>일반 셸 입력은 받지 않으며, 현재 프로젝트의 Codex 작업 로그만 표시합니다.</p>
        {isRunActive(run) ? (
          <button className="stop-button" type="button" onClick={onStop} disabled={run.status === "stopping"}>실행 중지</button>
        ) : (
          <button className="run-button" type="button" onClick={onStart} disabled={!runtime?.codexAvailable || starting}>
            {starting ? "Codex 시작 중…" : "Codex 작업 시작"}
          </button>
        )}
      </div>
    </section>
  );
}

export default function App() {
  const [projects, setProjects] = useState([]);
  const [legacy, setLegacy] = useState([]);
  const [project, setProject] = useState(null);
  const [selectedStageId, setSelectedStageId] = useState("sourcing");
  const [loading, setLoading] = useState(true);
  const [connectionError, setConnectionError] = useState("");
  const [showCreate, setShowCreate] = useState(false);
  const [toast, setToast] = useState("");
  const [saveStatus, setSaveStatus] = useState("saved");
  const [runtime, setRuntime] = useState(null);
  const [run, setRun] = useState(null);
  const [startingRun, setStartingRun] = useState(false);
  const [workspaceRevision, setWorkspaceRevision] = useState(0);
  const saveTimer = useRef(null);

  const progress = useMemo(() => project ? deriveProgress(project) : null, [project]);
  const selectedStage = progress?.stages.find((stage) => stage.id === selectedStageId) ?? progress?.stages[0];
  const record = project?.stageData?.[selectedStageId];

  async function loadWorkspace(selectId) {
    setLoading(true);
    try {
      const [{ projects: list }, { projects: legacyList }, runtimeState] = await Promise.all([
        api("/api/projects"),
        api("/api/legacy-projects"),
        api("/api/runtime"),
      ]);
      setProjects(list);
      setLegacy(legacyList);
      setRuntime(runtimeState);
      setConnectionError("");
      const target = selectId ?? project?.project?.id ?? list[0]?.projectId;
      if (target) {
        const [detail, { runs }] = await Promise.all([
          api(`/api/projects/${encodeURIComponent(target)}`),
          api(`/api/runs?projectId=${encodeURIComponent(target)}`),
        ]);
        setProject(detail);
        setRun(runs[0] ?? null);
        setSelectedStageId(detail.workflow.currentStage || "sourcing");
      } else {
        setProject(null);
        setRun(null);
      }
    } catch (error) {
      setConnectionError(error.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { loadWorkspace(); }, []);
  useEffect(() => () => clearTimeout(saveTimer.current), []);
  useEffect(() => {
    if (!toast) return undefined;
    const timer = setTimeout(() => setToast(""), 2400);
    return () => clearTimeout(timer);
  }, [toast]);
  useEffect(() => {
    if (!run?.runId || !isRunActive(run)) return undefined;
    let cancelled = false;
    let timer;
    const poll = async () => {
      try {
        const latest = await api(`/api/runs/${encodeURIComponent(run.runId)}`);
        if (!cancelled) {
          setRun(latest);
          if (shouldRefreshProjectAfterRun(latest)) {
            const refreshed = await api(`/api/projects/${encodeURIComponent(latest.projectId)}`);
            if (!cancelled) {
              setProject(refreshed);
              setProjects((current) => current.map((item) => (
                item.projectId === refreshed.project.id
                  ? {
                    ...item,
                    name: refreshed.project.name,
                    currentStage: refreshed.workflow.currentStage,
                    blockedReason: refreshed.workflow.blockedReason,
                    updatedAt: refreshed.project.updatedAt,
                  }
                  : item
              )));
            }
          }
        }
      } catch (error) {
        if (!cancelled) setToast(`Codex 로그 확인 실패: ${error.message}`);
      }
      if (!cancelled) timer = setTimeout(poll, 700);
    };
    timer = setTimeout(poll, 350);
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [run?.runId, run?.status]);

  function commit(next) {
    const synced = withDerivedWorkflow(next);
    setProject(synced);
    setSaveStatus("saving");
    clearTimeout(saveTimer.current);
    saveTimer.current = setTimeout(async () => {
      try {
        const saved = await api(`/api/projects/${encodeURIComponent(synced.project.id)}`, { method: "PUT", body: JSON.stringify(synced) });
        setProject(saved);
        setSaveStatus("saved");
        setProjects((current) => current.map((item) => item.projectId === saved.project.id ? {
          ...item,
          name: saved.project.name,
          currentStage: saved.workflow.currentStage,
          blockedReason: saved.workflow.blockedReason,
          updatedAt: saved.project.updatedAt,
        } : item));
      } catch (error) {
        setSaveStatus("error");
        setToast(`저장 실패: ${error.message}`);
      }
    }, 420);
  }

  async function selectProject(projectId) {
    try {
      const [detail, { runs }] = await Promise.all([
        api(`/api/projects/${encodeURIComponent(projectId)}`),
        api(`/api/runs?projectId=${encodeURIComponent(projectId)}`),
      ]);
      setProject(detail);
      setRun(runs[0] ?? null);
      setSelectedStageId(detail.workflow.currentStage || "sourcing");
    } catch (error) {
      setToast(error.message);
    }
  }

  function createdProject(created) {
    setShowCreate(false);
    setProject(created);
    setSelectedStageId("sourcing");
    loadWorkspace(created.project.id);
  }

  async function startCodex() {
    if (!project || !selectedStage || selectedStage.status === "locked") return;
    setStartingRun(true);
    try {
      clearTimeout(saveTimer.current);
      setSaveStatus("saving");
      const synced = withDerivedWorkflow(project);
      const saved = await api(`/api/projects/${encodeURIComponent(synced.project.id)}`, {
        method: "PUT",
        body: JSON.stringify(synced),
      });
      setProject(saved);
      setSaveStatus("saved");
      const started = await api("/api/runs", {
        method: "POST",
        body: JSON.stringify({
          projectId: saved.project.id,
          stageId: selectedStage.id,
          prompt: buildCodexPrompt(saved, selectedStage.id),
        }),
      });
      setRun(started);
      setToast("Codex 작업을 시작했습니다. 아래 콘솔에서 진행 상황을 확인하세요.");
    } catch (error) {
      setSaveStatus("error");
      setToast(`Codex 실행 실패: ${error.message}`);
    } finally {
      setStartingRun(false);
    }
  }

  async function stopCodex() {
    if (!run?.runId) return;
    try {
      const stopped = await api(`/api/runs/${encodeURIComponent(run.runId)}`, { method: "DELETE" });
      setRun(stopped);
      setToast("Codex 실행 중지를 요청했습니다.");
    } catch (error) {
      setToast(`Codex 중지 실패: ${error.message}`);
    }
  }

  function exportProject() {
    const blob = new Blob([`${JSON.stringify(project, null, 2)}\n`], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `${project.project.id}-project.json`;
    anchor.click();
    URL.revokeObjectURL(url);
  }

  function chooseSourcingCandidate(candidate) {
    try {
      commit(selectSourcingCandidate(project, candidate, candidate.recommendedPrice ?? ""));
      setToast(`${candidate.productName} 후보를 선택했습니다. 판매가를 확인해 주세요.`);
    } catch (error) {
      setToast(error.message);
    }
  }

  function confirmCandidateAndAdvance() {
    try {
      const next = confirmSourcingSelection(project);
      commit(next);
      setSelectedStageId("product-planning");
      setToast("상품과 가격을 저장하고 상품기획 단계로 이동했습니다.");
    } catch (error) {
      setToast(error.message);
    }
  }

  function continueFromSourcing() {
    try {
      const next = setStageCompleted(project, "sourcing", true);
      commit(next);
      setSelectedStageId("handoff");
      setToast("실제 소싱 결과를 확인했습니다. 상품과 가격을 선택해 주세요.");
    } catch (error) {
      setToast(error.message);
    }
  }

  if (loading) return <main className="loading-screen"><div className="loader" /><p>프로젝트를 불러오는 중입니다…</p></main>;
  if (connectionError) return (
    <main className="error-screen"><div className="brand-mark">CF</div><p className="eyebrow">LOCAL SERVER</p><h1>프로젝트 서버에 연결할 수 없어요</h1><p>{connectionError}</p><button className="primary-button" type="button" onClick={() => loadWorkspace()}>다시 연결</button></main>
  );

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="brand"><span className="brand-mark">CF</span><span><strong>Commerce Flow</strong><small>쿠팡 커머스 자동화</small></span></div>
        <div className="top-actions">
          <span className={`save-status ${saveStatus}`}>{saveStatus === "saving" ? "저장 중…" : saveStatus === "error" ? "저장 확인 필요" : "모든 변경 저장됨"}</span>
          {project && <button className="ghost-button" type="button" onClick={exportProject}>JSON 내보내기</button>}
          <button className="primary-button compact" type="button" onClick={() => setShowCreate(true)}>＋ 새 프로젝트</button>
        </div>
      </header>
      <ProjectRail projects={projects} activeId={project?.project?.id} onSelect={selectProject} onCreate={() => setShowCreate(true)} />

      {!project ? (
        <main className="welcome-panel">
          <p className="eyebrow">START HERE</p>
          <h1>상품 하나,<br />프로젝트 하나.</h1>
          <p>소싱부터 상세페이지와 판매 피드백까지 폴더와 현재 단계를 한곳에서 관리합니다.</p>
          <button className="primary-button" type="button" onClick={() => setShowCreate(true)}>첫 프로젝트 만들기</button>
          {legacy.length > 0 && <p className="legacy-hint">기존 detail-page 작업 {legacy.length}개를 감지했습니다. 이동하거나 삭제하지 않고 새 프로젝트에서 확인할 수 있습니다.</p>}
        </main>
      ) : (
        <main className="workspace">
          <section className="project-hero">
            <div>
              <p className="breadcrumb">프로젝트 / <strong>{project.project.id}</strong></p>
              <h1>{project.project.name}</h1>
              <div className="hero-tags"><span>{project.project.channel}</span><span>도매꾹 Best 고배수 pair 탐색</span><span>9단계 중 {progress.completedCount}단계 완료</span></div>
            </div>
            <div
              className="progress-summary"
              role="progressbar"
              aria-label={`프로젝트 진행률 ${progress.percentage}%`}
              aria-valuemin="0"
              aria-valuemax="100"
              aria-valuenow={progress.percentage}
            >
              <span><small>전체 진행률</small><strong>{progress.percentage}%</strong></span>
              <div className="progress-track" aria-hidden="true"><i style={{ width: `${progress.percentage}%` }} /></div>
              <p>{progress.completedCount}/9 단계 완료</p>
            </div>
          </section>

          <section className="workflow-overview">
            <div className="workflow-overview-head"><div><p className="eyebrow">WORKFLOW</p><h2>상품 출시까지 한 단계씩</h2></div><p><strong>{stageById(project.workflow.currentStage).step}</strong> {stageById(project.workflow.currentStage).title} 진행 중</p></div>
            <StageRail progress={progress} selectedId={selectedStage.id} onSelect={setSelectedStageId} />
          </section>

          <div className="workflow-grid">
            <section className="stage-panel">
              <div className="stage-panel-head">
                <div><p className="eyebrow">STEP {selectedStage.step}</p><h2>{selectedStage.title}</h2><p>{selectedStage.summary}</p></div>
                <span className={`availability ${AVAILABILITY[selectedStage.availability][1]}`}>{AVAILABILITY[selectedStage.availability][0]}</span>
              </div>

              <FlowSummary
                stage={selectedStage}
                run={run}
                runtime={runtime}
                starting={startingRun}
                onStart={startCodex}
              />

              {selectedStage.priorStageConfirmation && (selectedStage.status === "locked" || record.priorStageConfirmed) && (
                <label className={`prior-stage-confirmation ${record.priorStageConfirmed ? "checked" : ""}`}>
                  <input
                    type="checkbox"
                    checked={record.priorStageConfirmed === true}
                    onChange={(event) => commit(setPriorStageConfirmation(project, selectedStage.id, event.target.checked))}
                  />
                  <span className="custom-check">✓</span>
                  <span><strong>앞 단계 완료 확인</strong><small>{selectedStage.priorStageConfirmation} 이 확인은 외부 작업의 품질 검증을 대신하지 않으며, Codex가 근거를 다시 확인합니다.</small></span>
                </label>
              )}
              {selectedStage.status === "locked" && <div className="locked-banner"><span aria-hidden="true">!</span><p><strong>아직 이 단계를 실행할 수 없어요.</strong><br />현재 단계의 필수 입력과 승인을 먼저 완료하거나, 상품기획이라면 위에서 앞 단계 완료를 확인해 주세요.</p></div>}

              <div className="section-title"><span>01</span><div><h3>{selectedStage.id === "handoff" ? "후보 확인과 선택" : "이번 단계에 필요한 데이터"}</h3><p>{selectedStage.id === "handoff" ? "소싱 결과를 비교하고 다음 단계로 넘길 상품 하나를 고릅니다." : "아는 값만 정확히 입력하고, 모르면 비워 두세요."}</p></div></div>
              {selectedStage.id === "handoff" ? (
                <CandidateDecisionPanel
                  project={project}
                  disabled={selectedStage.status === "locked"}
                  onSelect={chooseSourcingCandidate}
                  onPriceChange={(value) => commit(updateStageInput(project, "handoff", "approvedPrice", value))}
                  onConfirm={confirmCandidateAndAdvance}
                  onReturnToSourcing={() => setSelectedStageId("sourcing")}
                />
              ) : (
                <div className="field-grid">
                  {selectedStage.inputs.map((input) => <FormField key={input.id} input={input} value={record.inputs[input.id]} disabled={selectedStage.status === "locked"} onChange={(value) => commit(updateStageInput(project, selectedStage.id, input.id, value))} />)}
                </div>
              )}

              {selectedStage.id === "product-planning" && selectedStage.status !== "locked" && (
                <aside className="planning-research-note">
                  <span aria-hidden="true">⌕</span>
                  <div><strong>경쟁사 저평점 리뷰는 Codex가 조사합니다.</strong><p>사용자는 리뷰 URL이나 조사 파일을 넣지 않습니다. Codex가 공개된 별점 1~3점 리뷰의 URL·조사시각·표본 범위와 반복 불만을 근거로 남깁니다.</p></div>
                </aside>
              )}

              {selectedStage.assetInput && selectedStage.status !== "locked" && (
                <WorkspaceViewer
                  project={project}
                  onToast={setToast}
                  variant="stage-assets"
                  refreshKey={workspaceRevision}
                  onAssetsChanged={() => setWorkspaceRevision((value) => value + 1)}
                />
              )}

              {selectedStage.status !== "locked" && selectedStage.id !== "handoff" && (
                <CodexConsole runtime={runtime} run={run} starting={startingRun} onStart={startCodex} onStop={stopCodex} />
              )}

              {selectedStage.id === "sourcing" ? (
                <SourcingResultPanel project={project} run={run} onContinue={continueFromSourcing} />
              ) : (
                <>
                  <div className="section-title"><span>02</span><div><h3>결과 확인과 승인</h3><p>현재 단계의 실제 결과와 승인 조건을 확인하세요.</p></div></div>
                  <ul className="acceptance-list">{selectedStage.acceptance.map((item) => <li key={item}><span>✓</span>{item}</li>)}</ul>

                  {selectedStage.approvalGate && selectedStage.id !== "handoff" && (
                    <label className={`approval-box ${record.approved ? "checked" : ""}`}>
                      <input type="checkbox" checked={record.approved} disabled={selectedStage.status === "locked"} onChange={(event) => commit(setStageApproval(project, selectedStage.id, event.target.checked))} />
                      <span className="custom-check">✓</span><span><strong>사용자 승인 게이트</strong><small>{selectedStage.approvalGate}</small></span>
                    </label>
                  )}

                  <label className="blocker-field">
                    <span>현재 차단 사유 <small>선택</small></span>
                    <input value={project.workflow.blockedReason ?? ""} onChange={(event) => commit({ ...project, workflow: { ...project.workflow, blockedReason: event.target.value || null } })} placeholder="예: 실제 SKU 정면 사진이 필요함" />
                  </label>

                  {selectedStage.id !== "handoff" && <div className="stage-actions">
                    {selectedStage.complete ? (
                      <button className="complete-button undo" type="button" onClick={() => commit(setStageCompleted(project, selectedStage.id, false))}>완료 취소</button>
                    ) : (
                      <button className="complete-button" type="button" disabled={!canCompleteStage(project, selectedStage.id)} onClick={() => {
                        const next = setStageCompleted(project, selectedStage.id, true);
                        commit(next);
                        const nextId = deriveProgress(next).currentStageId;
                        if (nextId) setSelectedStageId(nextId);
                        setToast("단계를 완료하고 다음 단계로 이동했습니다.");
                      }}>이 단계 완료</button>
                    )}
                  </div>}
                  {selectedStage.id !== "handoff" && selectedStage.missing.length > 0 && selectedStage.status === "current" && <p className="missing-note">아직 필요한 입력: {selectedStage.missing.map((input) => input.label).join(", ")}</p>}
                </>
              )}
            </section>
            <aside className="context-column">
              <WorkspaceViewer project={project} onToast={setToast} refreshKey={workspaceRevision} onAssetsChanged={() => setWorkspaceRevision((value) => value + 1)} />
              <FolderMap project={project} legacy={legacy} />
            </aside>
          </div>
        </main>
      )}
      {showCreate && <CreateProjectDialog onClose={() => setShowCreate(false)} onCreated={createdProject} />}
      {toast && <div className="toast" role="status">{toast}</div>}
    </div>
  );
}
