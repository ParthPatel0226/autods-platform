/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { JobResult } from '../models/JobResult';
import type { JobStatus } from '../models/JobStatus';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class JobsService {
    /**
     * Get job status
     * Return current status and progress for a background job.
     * @returns JobStatus Successful Response
     * @throws ApiError
     */
    public static getJobStatusJobsJobIdGet({
        jobId,
    }: {
        jobId: string,
    }): CancelablePromise<JobStatus> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/jobs/{job_id}',
            path: {
                'job_id': jobId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Cancel a job
     * Request cancellation of a pending or running job.
     * @returns any Successful Response
     * @throws ApiError
     */
    public static cancelJobJobsJobIdDelete({
        jobId,
    }: {
        jobId: string,
    }): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'DELETE',
            url: '/jobs/{job_id}',
            path: {
                'job_id': jobId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Get job result
     * Return the result payload for a completed job.
     * @returns JobResult Successful Response
     * @throws ApiError
     */
    public static getJobResultJobsJobIdResultGet({
        jobId,
    }: {
        jobId: string,
    }): CancelablePromise<JobResult> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/jobs/{job_id}/result',
            path: {
                'job_id': jobId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Stream job progress via SSE
     * Open a Server-Sent Events stream that emits JobProgressEvent updates until the job reaches a terminal state.
     * @returns any Successful Response
     * @throws ApiError
     */
    public static streamJobJobsJobIdStreamGet({
        jobId,
    }: {
        jobId: string,
    }): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/jobs/{job_id}/stream',
            path: {
                'job_id': jobId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
}
