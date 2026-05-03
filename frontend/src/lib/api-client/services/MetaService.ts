/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { AgentPromptsResponse } from '../models/AgentPromptsResponse';
import type { CostSummary } from '../models/CostSummary';
import type { DomainConfigList } from '../models/DomainConfigList';
import type { PipelineLogResponse } from '../models/PipelineLogResponse';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class MetaService {
    /**
     * Health
     * @returns any Successful Response
     * @throws ApiError
     */
    public static healthHealthGet(): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/health',
        });
    }
    /**
     * Root
     * @returns string Successful Response
     * @throws ApiError
     */
    public static rootGet(): CancelablePromise<Record<string, string>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/',
        });
    }
    /**
     * List registered tools
     * Return all registered tools with optional category/domain filter.
     * @returns any Successful Response
     * @throws ApiError
     */
    public static listToolsMetaToolsGet({
        category,
        domain,
    }: {
        /**
         * Filter by registry category
         */
        category?: (string | null),
        /**
         * Filter by domain name
         */
        domain?: (string | null),
    }): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/meta/tools',
            query: {
                'category': category,
                'domain': domain,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Get a single tool entry by registry key
     * Return full metadata for a tool by its registry key.
     * @returns any Successful Response
     * @throws ApiError
     */
    public static getToolMetaToolsToolNameGet({
        toolName,
    }: {
        toolName: string,
    }): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/meta/tools/{tool_name}',
            path: {
                'tool_name': toolName,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Get paginated pipeline log for a project
     * Return paginated pipeline log entries for a project (newest first).
     * @returns PipelineLogResponse Successful Response
     * @throws ApiError
     */
    public static getPipelineLogMetaPipelineLogProjectIdGet({
        projectId,
        limit = 200,
        offset,
    }: {
        projectId: string,
        /**
         * Max entries to return
         */
        limit?: number,
        /**
         * Number of entries to skip
         */
        offset?: number,
    }): CancelablePromise<PipelineLogResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/meta/pipeline-log/{project_id}',
            path: {
                'project_id': projectId,
            },
            query: {
                'limit': limit,
                'offset': offset,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Get API cost summary for a project
     * Return API call count, token count, and per-step cost breakdown.
     * @returns CostSummary Successful Response
     * @throws ApiError
     */
    public static getCostSummaryMetaCostsProjectIdGet({
        projectId,
    }: {
        projectId: string,
    }): CancelablePromise<CostSummary> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/meta/costs/{project_id}',
            path: {
                'project_id': projectId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * List all domain configurations
     * Return all domain configurations from domain_configs.yaml.
     * @returns DomainConfigList Successful Response
     * @throws ApiError
     */
    public static getDomainConfigsMetaDomainsGet(): CancelablePromise<DomainConfigList> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/meta/domains',
        });
    }
    /**
     * Get all agent prompts (admin)
     * Return all agent prompts from agent_prompts.yaml.
     *
     * Admin-only in production. Currently accepts any authenticated user.
     * TODO: add role/email check once a roles system is in place.
     * @returns AgentPromptsResponse Successful Response
     * @throws ApiError
     */
    public static getAgentPromptsMetaAgentPromptsGet(): CancelablePromise<AgentPromptsResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/meta/agent-prompts',
        });
    }
}
