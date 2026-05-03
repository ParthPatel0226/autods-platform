/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { FairnessReport } from '../models/FairnessReport';
import type { FairnessRequest } from '../models/FairnessRequest';
import type { ModelCardResponse } from '../models/ModelCardResponse';
import type { SHAPRequest } from '../models/SHAPRequest';
import type { WhatIfRequest } from '../models/WhatIfRequest';
import type { WhatIfResponse } from '../models/WhatIfResponse';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class ExplainabilityService {
    /**
     * Compute SHAP values (sync ≤50 rows, async >50 rows)
     * Return SHAP values synchronously for small samples; launch background job for large ones.
     * @returns any Successful Response
     * @throws ApiError
     */
    public static computeShapExplainShapPost({
        requestBody,
    }: {
        requestBody: SHAPRequest,
    }): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/explain/shap',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Run a what-if analysis by modifying feature values
     * Apply feature modifications to a base row and compare predictions.
     * @returns WhatIfResponse Successful Response
     * @throws ApiError
     */
    public static whatifExplainWhatifPost({
        requestBody,
    }: {
        requestBody: WhatIfRequest,
    }): CancelablePromise<WhatIfResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/explain/whatif',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Run fairness audit on the best model
     * Compute disparate-impact and group-fairness metrics for protected attributes.
     * @returns FairnessReport Successful Response
     * @throws ApiError
     */
    public static fairnessAuditExplainFairnessPost({
        requestBody,
    }: {
        requestBody: FairnessRequest,
    }): CancelablePromise<FairnessReport> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/explain/fairness',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Retrieve or generate model card for a project
     * Return the standardised model card (Google model card format) for the project.
     * @returns ModelCardResponse Successful Response
     * @throws ApiError
     */
    public static getModelCardExplainModelCardProjectIdGet({
        projectId,
    }: {
        projectId: string,
    }): CancelablePromise<ModelCardResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/explain/model-card/{project_id}',
            path: {
                'project_id': projectId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
}
