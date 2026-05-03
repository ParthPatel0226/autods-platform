// Re-export all generated types from the OpenAPI client
export type {
  _JoinSuggestRequest,
  AgentPromptsResponse,
  ApplyJoinResponse,
  BatchPredictRequest,
  BatchPredictResponse,
  Body_upload_file_upload_file_post,
  ChatHistory,
  ChatMessage,
  ChatResponse,
  ChatSendRequest,
  ConfidenceInterval,
  ConfigureRequest,
  ConnectorUploadRequest,
  CostSummary,
  CreateProjectRequest,
  DomainAlternative,
  DomainConfig,
  DomainConfigList,
  DomainDetectionResponse,
  EDAAnswerRequest,
  EDAQuestion,
  EDAQuestionOption,
  EDAResults,
  EDARunRequest,
  FairnessReport,
  FairnessRequest,
  FEApplyRequest,
  FEResults,
  FESuggestion,
  FESuggestResponse,
  HTTPValidationError,
  JobResult,
  JobStatus,
  JoinKey,
  JoinPlan,
  Leaderboard,
  LoginRequest,
  ModelCardResponse,
  ModelEntry,
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
  SuggestedAction,
  SuggestJoinResponse,
  TokenResponse,
  TrainRequest,
  UpdateProjectRequest,
  UploadFileResponse,
  User,
  ValidationError,
  WhatIfRequest,
  WhatIfResponse,
} from "@/lib/api-client";

// Types present in the backend but not in the generated OpenAPI client

export type SHAPResponse = {
  global_importance: Record<string, number>;
  local_examples: Array<Record<string, unknown>>;
  interactions?: Record<string, unknown> | null;
};

export type JobProgressEvent = {
  job_id: string;
  status: string;
  progress: number;
  message: string;
  timestamp: string;
};

export type ReportResponse = {
  report_id: string;
  download_url: string;
  format: "html" | "pdf" | "notebook" | "executive_summary";
  generated_at: string;
};

export type PipelineLogEntry = {
  timestamp: string;
  step: string;
  tool: string;
  params: Record<string, unknown>;
  duration_seconds: number;
  status: string;
  error?: string | null;
};
