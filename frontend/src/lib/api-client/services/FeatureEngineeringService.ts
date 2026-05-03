/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { FEApplyRequest } from '../models/FEApplyRequest';
import type { FEResults } from '../models/FEResults';
import type { FESuggestResponse } from '../models/FESuggestResponse';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class FeatureEngineeringService {
    /**
     * Get per-column feature engineering suggestions
     * Return domain-aware FE suggestions for each column in the project.
     * @returns FESuggestResponse Successful Response
     * @throws ApiError
     */
    public static suggestDecisionsFeSuggestPost({
        projectId,
    }: {
        projectId: string,
    }): CancelablePromise<FESuggestResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/fe/suggest',
            query: {
                'project_id': projectId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Apply feature engineering decisions in the background
     * Store FE decisions and launch feature engineering as a background job.
     * @returns any Successful Response
     * @throws ApiError
     */
    public static applyDecisionsFeApplyPost({
        requestBody,
    }: {
        requestBody: FEApplyRequest,
    }): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/fe/apply',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Retrieve completed feature engineering results
     * Return FE results once the background job completes.
     * @returns FEResults Successful Response
     * @throws ApiError
     */
    public static getResultsFeResultsProjectIdGet({
        projectId,
    }: {
        projectId: string,
    }): CancelablePromise<FEResults> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/fe/results/{project_id}',
            path: {
                'project_id': projectId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
}
