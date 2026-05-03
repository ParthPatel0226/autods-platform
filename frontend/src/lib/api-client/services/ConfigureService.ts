/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ConfigureRequest } from '../models/ConfigureRequest';
import type { DomainDetectionResponse } from '../models/DomainDetectionResponse';
import type { Project } from '../models/Project';
import type { StartPipelineResponse } from '../models/StartPipelineResponse';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class ConfigureService {
    /**
     * Auto-detect domain from uploaded data
     * Run domain detection on the project's loaded data sources.
     * @returns DomainDetectionResponse Successful Response
     * @throws ApiError
     */
    public static detectDomainConfigureDetectDomainPost({
        projectId,
    }: {
        projectId: string,
    }): CancelablePromise<DomainDetectionResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/configure/detect-domain',
            query: {
                'project_id': projectId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Set target column, problem type, user mode, and goal
     * Apply domain, target, problem type, user mode, and goal to the project.
     * @returns Project Successful Response
     * @throws ApiError
     */
    public static setTargetConfigureSetTargetPost({
        requestBody,
    }: {
        requestBody: ConfigureRequest,
    }): CancelablePromise<Project> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/configure/set-target',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Mark configuration complete and advance to first pipeline step
     * Advance the project to the EDA step and set workflow_status=active.
     * @returns StartPipelineResponse Successful Response
     * @throws ApiError
     */
    public static startPipelineConfigureStartPipelinePost({
        projectId,
    }: {
        projectId: string,
    }): CancelablePromise<StartPipelineResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/configure/start-pipeline',
            query: {
                'project_id': projectId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
}
