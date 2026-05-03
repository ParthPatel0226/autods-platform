/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { BatchPredictRequest } from '../models/BatchPredictRequest';
import type { BatchPredictResponse } from '../models/BatchPredictResponse';
import type { PredictRequest } from '../models/PredictRequest';
import type { PredictResponse } from '../models/PredictResponse';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class PredictService {
    /**
     * Predict a single row using the project's best model
     * Load best model and return prediction + optional SHAP values for one row.
     * @returns PredictResponse Successful Response
     * @throws ApiError
     */
    public static predictSinglePredictSinglePost({
        requestBody,
    }: {
        requestBody: PredictRequest,
    }): CancelablePromise<PredictResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/predict/single',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Start batch prediction in the background
     * Schedule batch inference as a background job; returns job_id and row count.
     * @returns BatchPredictResponse Successful Response
     * @throws ApiError
     */
    public static predictBatchPredictBatchPost({
        requestBody,
    }: {
        requestBody: BatchPredictRequest,
    }): CancelablePromise<BatchPredictResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/predict/batch',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
}
