/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { _JoinSuggestRequest } from '../models/_JoinSuggestRequest';
import type { ApplyJoinResponse } from '../models/ApplyJoinResponse';
import type { Body_upload_file_upload_file_post } from '../models/Body_upload_file_upload_file_post';
import type { ConnectorUploadRequest } from '../models/ConnectorUploadRequest';
import type { JoinPlan } from '../models/JoinPlan';
import type { SampleDatasetInfo } from '../models/SampleDatasetInfo';
import type { SampleDatasetRequest } from '../models/SampleDatasetRequest';
import type { SuggestJoinResponse } from '../models/SuggestJoinResponse';
import type { UploadFileResponse } from '../models/UploadFileResponse';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class UploadService {
    /**
     * Upload File
     * Upload a file and load it into the session source cache.
     * @returns UploadFileResponse Successful Response
     * @throws ApiError
     */
    public static uploadFileUploadFilePost({
        projectId,
        formData,
    }: {
        /**
         * Project to attach this source to
         */
        projectId: string,
        formData: Body_upload_file_upload_file_post,
    }): CancelablePromise<UploadFileResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/upload/file',
            query: {
                'project_id': projectId,
            },
            formData: formData,
            mediaType: 'multipart/form-data',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * List Samples
     * List all built-in sample datasets (no auth required).
     * @returns SampleDatasetInfo Successful Response
     * @throws ApiError
     */
    public static listSamplesUploadSamplesGet(): CancelablePromise<Array<SampleDatasetInfo>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/upload/samples',
        });
    }
    /**
     * Load Sample
     * Load a built-in sample dataset into the session source cache.
     * @returns UploadFileResponse Successful Response
     * @throws ApiError
     */
    public static loadSampleUploadSamplesPost({
        projectId,
        requestBody,
    }: {
        /**
         * Project to attach this source to
         */
        projectId: string,
        requestBody: SampleDatasetRequest,
    }): CancelablePromise<UploadFileResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/upload/samples',
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
     * Load Connector
     * Load data via a named connector (database, API, cloud, etc.).
     * @returns UploadFileResponse Successful Response
     * @throws ApiError
     */
    public static loadConnectorUploadConnectorPost({
        projectId,
        requestBody,
    }: {
        /**
         * Project to attach this source to
         */
        projectId: string,
        requestBody: ConnectorUploadRequest,
    }): CancelablePromise<UploadFileResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/upload/connector',
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
     * Suggest Join
     * Suggest join keys for two cached sources.
     * @returns SuggestJoinResponse Successful Response
     * @throws ApiError
     */
    public static suggestJoinUploadJoinSuggestPost({
        requestBody,
    }: {
        requestBody: _JoinSuggestRequest,
    }): CancelablePromise<SuggestJoinResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/upload/join/suggest',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Apply Join
     * Execute a join between two cached sources and cache the result.
     * @returns ApplyJoinResponse Successful Response
     * @throws ApiError
     */
    public static applyJoinUploadJoinApplyPost({
        projectId,
        requestBody,
    }: {
        /**
         * Project that owns these sources
         */
        projectId: string,
        requestBody: JoinPlan,
    }): CancelablePromise<ApplyJoinResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/upload/join/apply',
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
     * Preview Source
     * Return the first N rows of a cached source as JSON records.
     * @returns any Successful Response
     * @throws ApiError
     */
    public static previewSourceUploadPreviewSourceIdGet({
        sourceId,
        projectId,
        n = 50,
    }: {
        sourceId: string,
        /**
         * Project that owns this source
         */
        projectId: string,
        n?: number,
    }): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/upload/preview/{source_id}',
            path: {
                'source_id': sourceId,
            },
            query: {
                'project_id': projectId,
                'n': n,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
}
