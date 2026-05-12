import { api } from "../api";
import type {
  _JoinSuggestRequest,
  AgentPromptsResponse,
  ApplyJoinResponse,
  BatchPredictRequest,
  BatchPredictResponse,
  ChatHistory,
  ChatResponse,
  ChatSendRequest,
  ConfigureRequest,
  ConnectorUploadRequest,
  CostSummary,
  CreateProjectRequest,
  DomainConfigList,
  DomainDetectionResponse,
  EDAAnswerRequest,
  EDAQuestion,
  EDAResults,
  EDARunRequest,
  FairnessReport,
  FairnessRequest,
  FEApplyRequest,
  FEResults,
  FESuggestResponse,
  JobResult,
  JobStatus,
  JoinPlan,
  Leaderboard,
  LoginRequest,
  ModelCardResponse,
  ModelingConfig,
  PipelineLogResponse,
  PredictRequest,
  PredictResponse,
  Project,
  ProjectListItem,
  ReportJobResponse,
  ReportRequest,
  SampleDatasetInfo,
  SampleDatasetRequest,
  SelectBestRequest,
  SHAPRequest,
  SignupRequest,
  StartPipelineResponse,
  SuggestJoinResponse,
  TokenResponse,
  TrainRequest,
  UpdateProjectRequest,
  UploadFileResponse,
  User,
  WhatIfRequest,
  WhatIfResponse,
} from "./types";
import type {
  JobProgressEvent,
  ReportResponse,
  SHAPResponse,
} from "./types";

// ─── Auth ────────────────────────────────────────────────────────────────────

export const authApi = {
  signup: (body: SignupRequest) =>
    api.post<TokenResponse>("/auth/signup", body),
  login: (body: LoginRequest) =>
    api.post<TokenResponse>("/auth/login", body),
  me: () => api.get<User>("/auth/me"),
};

// ─── Projects ────────────────────────────────────────────────────────────────

export const projectsApi = {
  list: () => api.get<ProjectListItem[]>("/projects/"),
  create: (body: CreateProjectRequest) =>
    api.post<Project>("/projects/", body),
  get: (id: string) => api.get<Project>(`/projects/${id}`),
  update: (id: string, body: UpdateProjectRequest) =>
    api.patch<Project>(`/projects/${id}`, body),
  delete: (id: string) => api.del<Record<string, unknown>>(`/projects/${id}`),
  activate: (id: string) =>
    api.post<Record<string, unknown>>(`/projects/${id}/activate`),
};

// ─── Upload ──────────────────────────────────────────────────────────────────

export const uploadApi = {
  file: (form: FormData) =>
    api.upload<UploadFileResponse>("/upload/file", form),
  listSamples: () => api.get<SampleDatasetInfo[]>("/upload/samples"),
  loadSample: (body: SampleDatasetRequest) =>
    api.post<UploadFileResponse>("/upload/samples", body),
  connector: (body: ConnectorUploadRequest) =>
    api.post<UploadFileResponse>("/upload/connector", body),
  suggestJoin: (body: _JoinSuggestRequest) =>
    api.post<SuggestJoinResponse>("/upload/join/suggest", body),
  applyJoin: (body: JoinPlan) =>
    api.post<ApplyJoinResponse>("/upload/join/apply", body),
  preview: (sourceId: string) =>
    api.get<Record<string, unknown>>(`/upload/preview/${sourceId}`),
};

// ─── Configure ───────────────────────────────────────────────────────────────

export const configureApi = {
  detectDomain: (body: ConfigureRequest) =>
    api.post<DomainDetectionResponse>("/configure/detect-domain", body),
  setTarget: (body: ConfigureRequest) =>
    api.post<Record<string, unknown>>("/configure/set-target", body),
  startPipeline: (body: ConfigureRequest) =>
    api.post<StartPipelineResponse>("/configure/start-pipeline", body),
};

// ─── EDA ─────────────────────────────────────────────────────────────────────

export const edaApi = {
  generateQuestions: (body: { project_id: string }) =>
    api.post<{ questions: EDAQuestion[] }>("/eda/generate-questions", body),
  answerQuestions: (body: EDAAnswerRequest) =>
    api.post<Record<string, unknown>>("/eda/answer", body),
  run: (body: EDARunRequest) =>
    api.post<Record<string, unknown>>("/eda/run", body),
  results: (projectId: string) =>
    api.get<EDAResults>(`/eda/results/${projectId}`),
};

// ─── Feature Engineering ─────────────────────────────────────────────────────

export const feApi = {
  suggest: (body: { project_id: string }) =>
    api.post<FESuggestResponse>("/fe/suggest", body),
  apply: (body: FEApplyRequest) =>
    api.post<Record<string, unknown>>("/fe/apply", body),
  results: (projectId: string) =>
    api.get<FEResults>(`/fe/results/${projectId}`),
};

// ─── Modeling ────────────────────────────────────────────────────────────────

export const modelingApi = {
  configure: (body: ModelingConfig) =>
    api.post<Record<string, unknown>>("/modeling/configure", body),
  train: (body: TrainRequest) =>
    api.post<Record<string, unknown>>("/modeling/train", body),
  leaderboard: (projectId: string) =>
    api.get<Leaderboard>(`/modeling/leaderboard/${projectId}`),
  selectBest: (body: SelectBestRequest) =>
    api.post<Record<string, unknown>>("/modeling/select-best", body),
};

// ─── Explainability ──────────────────────────────────────────────────────────

export const explainApi = {
  shap: (body: SHAPRequest) =>
    api.post<SHAPResponse>("/explain/shap", body),
  whatif: (body: WhatIfRequest) =>
    api.post<WhatIfResponse>("/explain/whatif", body),
  fairness: (body: FairnessRequest) =>
    api.post<FairnessReport>("/explain/fairness", body),
  modelCard: (projectId: string) =>
    api.get<ModelCardResponse>(`/explain/model-card/${projectId}`),
};

// ─── Predict ─────────────────────────────────────────────────────────────────

export const predictApi = {
  single: (body: PredictRequest) =>
    api.post<PredictResponse>("/predict/single", body),
  batch: (body: BatchPredictRequest) =>
    api.post<BatchPredictResponse>("/predict/batch", body),
};

// ─── Chat ────────────────────────────────────────────────────────────────────

export const chatApi = {
  send: (body: ChatSendRequest) =>
    api.post<ChatResponse>("/chat/message", body),
  history: (projectId: string) =>
    api.get<ChatHistory>(`/chat/history/${projectId}`),
  clear: (projectId: string) =>
    api.del<Record<string, unknown>>(`/chat/history/${projectId}`),
};

// ─── Download ────────────────────────────────────────────────────────────────

export const downloadApi = {
  generate: (body: ReportRequest) =>
    api.post<ReportJobResponse>("/download/report", body),
  download: (reportId: string) =>
    api.get<ReportResponse>(`/download/file/${reportId}`),
};

// ─── Jobs ────────────────────────────────────────────────────────────────────

export const jobsApi = {
  status: (jobId: string) => api.get<JobStatus>(`/jobs/${jobId}`),
  cancel: (jobId: string) =>
    api.del<Record<string, unknown>>(`/jobs/${jobId}`),
  result: (jobId: string) => api.get<JobResult>(`/jobs/${jobId}/result`),
  /** Open an SSE stream for live job progress. Caller must close the EventSource. */
  stream: (
    jobId: string,
    onEvent: (ev: JobProgressEvent) => void,
    onError?: (e: Event) => void,
  ): EventSource => {
    const base = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/v1";
    const token =
      typeof window !== "undefined"
        ? localStorage.getItem("autods_token")
        : null;
    const qs = token ? `?token=${encodeURIComponent(token)}` : "";
    const es = new EventSource(`${base}/jobs/${jobId}/stream${qs}`);
    es.onmessage = (e) => {
      try {
        onEvent(JSON.parse(e.data) as JobProgressEvent);
      } catch {
        // ignore malformed events
      }
    };
    if (onError) es.onerror = onError;
    return es;
  },
};

// ─── Meta ────────────────────────────────────────────────────────────────────

export const metaApi = {
  health: () => api.get<Record<string, unknown>>("/health"),
  tools: (category?: string, domain?: string) => {
    const q = new URLSearchParams();
    if (category) q.set("category", category);
    if (domain) q.set("domain", domain);
    const qs = q.toString();
    return api.get<Record<string, unknown>>(
      `/meta/tools${qs ? `?${qs}` : ""}`,
    );
  },
  tool: (name: string) =>
    api.get<Record<string, unknown>>(`/meta/tools/${name}`),
  pipelineLog: (projectId: string, limit = 200, offset = 0) =>
    api.get<PipelineLogResponse>(
      `/meta/pipeline-log/${projectId}?limit=${limit}&offset=${offset}`,
    ),
  costs: (projectId: string) =>
    api.get<CostSummary>(`/meta/costs/${projectId}`),
  domains: () => api.get<DomainConfigList>("/meta/domains"),
  agentPrompts: () => api.get<AgentPromptsResponse>("/meta/agent-prompts"),
};
