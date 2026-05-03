/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { EDAAnswerRequest } from '../models/EDAAnswerRequest';
import type { EDAQuestion } from '../models/EDAQuestion';
import type { EDAResults } from '../models/EDAResults';
import type { EDARunRequest } from '../models/EDARunRequest';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class EdaService {
    /**
     * Generate domain-aware EDA questions for the project
     * Return interactive EDA questions based on domain and data profile.
     * @returns EDAQuestion Successful Response
     * @throws ApiError
     */
    public static generateQuestionsEdaGenerateQuestionsPost({
        projectId,
    }: {
        projectId: string,
    }): CancelablePromise<Array<EDAQuestion>> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/eda/generate-questions',
            query: {
                'project_id': projectId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Submit answers to EDA questions
     * Store user answers to EDA questions in project state.
     * @returns any Successful Response
     * @throws ApiError
     */
    public static answerQuestionsEdaAnswerPost({
        requestBody,
    }: {
        requestBody: EDAAnswerRequest,
    }): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/eda/answer',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Start EDA analysis in the background
     * Launch EDA execution as a background task and return the job_id.
     * @returns any Successful Response
     * @throws ApiError
     */
    public static runEdaEdaRunPost({
        requestBody,
    }: {
        requestBody: EDARunRequest,
    }): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/eda/run',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Retrieve completed EDA results
     * Return EDA analysis results once the background job completes.
     * @returns EDAResults Successful Response
     * @throws ApiError
     */
    public static getResultsEdaResultsProjectIdGet({
        projectId,
    }: {
        projectId: string,
    }): CancelablePromise<EDAResults> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/eda/results/{project_id}',
            path: {
                'project_id': projectId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
}
