/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { Leaderboard } from '../models/Leaderboard';
import type { SelectBestRequest } from '../models/SelectBestRequest';
import type { TrainRequest } from '../models/TrainRequest';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class ModelingService {
    /**
     * Configure modeling: algorithms, metric, validation strategy
     * Merge user model configuration into project state and return an ETA estimate.
     * @returns any Successful Response
     * @throws ApiError
     */
    public static configureModelingModelingConfigurePost({
        projectId,
        requestBody,
    }: {
        projectId: string,
        requestBody: Record<string, any>,
    }): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/modeling/configure',
            query: {
                'project_id': projectId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Start model training in the background
     * Schedule model training as a background job and return the job_id.
     * @returns any Successful Response
     * @throws ApiError
     */
    public static trainModelsModelingTrainPost({
        requestBody,
    }: {
        requestBody: TrainRequest,
    }): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/modeling/train',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Retrieve model leaderboard for a project
     * Return all trained model results ranked by primary metric.
     * @returns Leaderboard Successful Response
     * @throws ApiError
     */
    public static getLeaderboardModelingLeaderboardProjectIdGet({
        projectId,
    }: {
        projectId: string,
    }): CancelablePromise<Leaderboard> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/modeling/leaderboard/{project_id}',
            path: {
                'project_id': projectId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Override best-model selection for a project
     * Persist a user-chosen model as the project best model.
     * @returns any Successful Response
     * @throws ApiError
     */
    public static selectBestModelingSelectBestPost({
        requestBody,
    }: {
        requestBody: SelectBestRequest,
    }): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/modeling/select-best',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
}
