"""api/schemas — all Pydantic request/response models.

Import everything from here:
    from api.schemas import LoginRequest, Project, ...
or wildcard:
    from api.schemas import *
"""

from .audit import (
    CostSummary,
    PipelineLogEntry,
    PipelineLogResponse,
)
from .auth import (
    LoginRequest,
    SignupRequest,
    TokenResponse,
    User,
)
from .chat import (
    ChatHistory,
    ChatMessage,
    ChatResponse,
    ChatSendRequest,
    SuggestedAction,
)
from .configs import (
    AgentPromptsResponse,
    DomainConfig,
    DomainConfigList,
)
from .configure import (
    ConfigureRequest,
    DomainAlternative,
    DomainDetectionResponse,
    StartPipelineResponse,
)
from .download import (
    ReportFormat,
    ReportJobResponse,
    ReportRequest,
    ReportResponse,
)
from .eda import (
    EDAAnswerRequest,
    EDAQuestion,
    EDAQuestionOption,
    EDAResults,
    EDARunRequest,
)
from .explainability import (
    FairnessReport,
    FairnessRequest,
    ModelCardResponse,
    SHAPRequest,
    SHAPResponse,
    WhatIfRequest,
    WhatIfResponse,
)
from .feature_engineering import (
    FEApplyRequest,
    FEResults,
    FESuggestion,
    FESuggestResponse,
)
from .jobs import (
    JobProgressEvent,
    JobResult,
    JobStatus,
)
from .modeling import (
    Leaderboard,
    ModelEntry,
    ModelingConfig,
    SelectBestRequest,
    TrainRequest,
)
from .predict import (
    BatchPredictRequest,
    BatchPredictResponse,
    ConfidenceInterval,
    PredictRequest,
    PredictResponse,
)
from .projects import (
    CreateProjectRequest,
    Project,
    ProjectListItem,
    UpdateProjectRequest,
)
from .tools import (
    ToolEntry,
    ToolListResponse,
    ToolParameter,
)
from .upload import (
    ApplyJoinResponse,
    ConnectorUploadRequest,
    DataSource,
    JoinKey,
    JoinPlan,
    SampleDatasetInfo,
    SampleDatasetRequest,
    SuggestJoinResponse,
    UploadFileResponse,
)

__all__ = [
    # audit
    "CostSummary",
    "PipelineLogEntry",
    "PipelineLogResponse",
    # auth
    "LoginRequest",
    "SignupRequest",
    "TokenResponse",
    "User",
    # chat
    "ChatHistory",
    "ChatMessage",
    "ChatResponse",
    "ChatSendRequest",
    "SuggestedAction",
    # configs
    "AgentPromptsResponse",
    "DomainConfig",
    "DomainConfigList",
    # configure
    "ConfigureRequest",
    "DomainAlternative",
    "DomainDetectionResponse",
    "StartPipelineResponse",
    # download
    "ReportFormat",
    "ReportJobResponse",
    "ReportRequest",
    "ReportResponse",
    # eda
    "EDAAnswerRequest",
    "EDAQuestion",
    "EDAQuestionOption",
    "EDAResults",
    "EDARunRequest",
    # explainability
    "FairnessReport",
    "FairnessRequest",
    "ModelCardResponse",
    "SHAPRequest",
    "SHAPResponse",
    "WhatIfRequest",
    "WhatIfResponse",
    # feature_engineering
    "FEApplyRequest",
    "FEResults",
    "FESuggestion",
    "FESuggestResponse",
    # jobs
    "JobProgressEvent",
    "JobResult",
    "JobStatus",
    # modeling
    "Leaderboard",
    "ModelEntry",
    "ModelingConfig",
    "SelectBestRequest",
    "TrainRequest",
    # predict
    "BatchPredictRequest",
    "BatchPredictResponse",
    "ConfidenceInterval",
    "PredictRequest",
    "PredictResponse",
    # projects
    "CreateProjectRequest",
    "Project",
    "ProjectListItem",
    "UpdateProjectRequest",
    # tools
    "ToolEntry",
    "ToolListResponse",
    "ToolParameter",
    # upload
    "ApplyJoinResponse",
    "ConnectorUploadRequest",
    "DataSource",
    "JoinKey",
    "JoinPlan",
    "SampleDatasetInfo",
    "SampleDatasetRequest",
    "SuggestJoinResponse",
    "UploadFileResponse",
]
