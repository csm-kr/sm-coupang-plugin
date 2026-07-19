import { useEffect, useMemo, useRef, useState } from "react";
import {
  PROJECT_ID_PATTERN,
  STAGES,
  buildCodexPrompt,
  canCompleteStage,
  createDefaultProjectId,
  deriveProgress,
  formatCodexEvent,
  isRunActive,
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

function CreateProjectDialog({ onClose, onCreated }) {
  const [form, setForm] = useState(() => ({
    projectId: createDefaultProjectId(),
    name: "",
    channel: "coupang",
    sourcingMode: "standard",
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
              <span>탐색 방식</span>
              <select value={form.sourcingMode} onChange={(event) => setForm({ ...form, sourcingMode: event.target.value })}>
                <option value="standard">일반 소싱</option>
                <option value="high-markup">Best 고배수 탐색</option>
              </select>
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
    <nav className="stage-rail" aria-label="프로젝트 단계">
      {progress.stages.map((stage) => (
        <button key={stage.id} type="button" onClick={() => onSelect(stage.id)} className={`stage-item ${stage.status} ${selectedId === stage.id ? "selected" : ""}`}>
          <span className="stage-number">{stage.complete ? "✓" : stage.step}</span>
          <span><strong>{stage.shortTitle}</strong><small>{stage.status === "locked" ? "앞 단계 대기" : AVAILABILITY[stage.availability][0]}</small></span>
        </button>
      ))}
    </nav>
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
      <input id={id} type={input.type} value={value ?? ""} disabled={disabled} placeholder={input.placeholder} onChange={(event) => onChange(event.target.value)} />
      {input.suffix && <span>{input.suffix}</span>}
    </div>
  );
  return <label className="field-label" htmlFor={id}><span>{input.label}<b>필수</b></span>{control}</label>;
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
        {(project.links?.reportRuns ?? []).length === 0 ? <span>연결된 보고서 없음</span> : project.links.reportRuns.map((path) => <code key={path}>{path}</code>)}
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
        if (!cancelled) setRun(latest);
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

  if (loading) return <main className="loading-screen"><div className="loader" /><p>프로젝트를 불러오는 중입니다…</p></main>;
  if (connectionError) return (
    <main className="error-screen"><div className="brand-mark">CO</div><p className="eyebrow">LOCAL SERVER</p><h1>프로젝트 서버에 연결할 수 없어요</h1><p>{connectionError}</p><button className="primary-button" type="button" onClick={() => loadWorkspace()}>다시 연결</button></main>
  );

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="brand"><span className="brand-mark">CO</span><span><strong>Commerce OS</strong><small>쿠팡 워크플로 대시보드</small></span></div>
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
              <div className="hero-tags"><span>{project.project.channel}</span><span>{project.project.sourcingMode === "high-markup" ? "Best 고배수 탐색" : "일반 소싱"}</span><span>9단계 중 {progress.completedCount}단계 완료</span></div>
            </div>
            <div className="progress-dial" style={{ "--progress": `${progress.percentage * 3.6}deg` }}><span><strong>{progress.percentage}%</strong><small>진행률</small></span></div>
          </section>

          <div className="workflow-grid">
            <StageRail progress={progress} selectedId={selectedStage.id} onSelect={setSelectedStageId} />
            <section className="stage-panel">
              <div className="stage-panel-head">
                <div><p className="eyebrow">STEP {selectedStage.step}</p><h2>{selectedStage.title}</h2><p>{selectedStage.summary}</p></div>
                <span className={`availability ${AVAILABILITY[selectedStage.availability][1]}`}>{AVAILABILITY[selectedStage.availability][0]}</span>
              </div>

              {selectedStage.status === "locked" && <div className="locked-banner"><span>🔒</span><p><strong>아직 이 단계를 실행할 수 없어요.</strong><br />현재 단계의 필수 입력과 승인을 먼저 완료해 주세요.</p></div>}

              <div className="section-title"><span>01</span><div><h3>이번 단계에 필요한 데이터</h3><p>아는 값만 정확히 입력하고, 모르면 비워 두세요.</p></div></div>
              <div className="field-grid">
                {selectedStage.inputs.map((input) => <FormField key={input.id} input={input} value={record.inputs[input.id]} disabled={selectedStage.status === "locked"} onChange={(value) => commit(updateStageInput(project, selectedStage.id, input.id, value))} />)}
              </div>

              <div className="section-title"><span>02</span><div><h3>완료 기준</h3><p>Codex의 실제 결과와 비교해 확인하세요.</p></div></div>
              <ul className="acceptance-list">{selectedStage.acceptance.map((item) => <li key={item}><span>✓</span>{item}</li>)}</ul>

              {selectedStage.approvalGate && (
                <label className={`approval-box ${record.approved ? "checked" : ""}`}>
                  <input type="checkbox" checked={record.approved} disabled={selectedStage.status === "locked"} onChange={(event) => commit(setStageApproval(project, selectedStage.id, event.target.checked))} />
                  <span className="custom-check">✓</span><span><strong>사용자 승인 게이트</strong><small>{selectedStage.approvalGate}</small></span>
                </label>
              )}

              <label className="blocker-field">
                <span>현재 차단 사유 <small>선택</small></span>
                <input value={project.workflow.blockedReason ?? ""} onChange={(event) => commit({ ...project, workflow: { ...project.workflow, blockedReason: event.target.value || null } })} placeholder="예: 실제 SKU 정면 사진이 필요함" />
              </label>

              <div className="stage-actions">
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
              </div>
              {selectedStage.missing.length > 0 && selectedStage.status === "current" && <p className="missing-note">아직 필요한 입력: {selectedStage.missing.map((input) => input.label).join(", ")}</p>}
              {selectedStage.status !== "locked" && (
                <CodexConsole runtime={runtime} run={run} starting={startingRun} onStart={startCodex} onStop={stopCodex} />
              )}
            </section>
            <aside className="context-column">
              <section className="side-card now-card"><p className="eyebrow">NOW</p><span className="now-step">{stageById(project.workflow.currentStage).step}</span><h3>지금 할 일</h3><p>{stageById(project.workflow.currentStage).summary}</p>{project.workflow.blockedReason && <div className="current-blocker"><strong>확인 필요</strong><span>{project.workflow.blockedReason}</span></div>}</section>
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
