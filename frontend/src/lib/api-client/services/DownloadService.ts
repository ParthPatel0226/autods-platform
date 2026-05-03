/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ReportJobResponse } from '../models/ReportJobResponse';
import type { ReportRequest } from '../models/ReportRequest';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class DownloadService {
    /**
     * Enqueue a report generation job
     * Schedule report generation as a background job and return the job_id.
     * @returns ReportJobResponse Successful Response
     * @throws ApiError
     */
    public static generateReportDownloadReportPost({
        requestBody,
    }: {
        requestBody: ReportRequest,
    }): CancelablePromise<ReportJobResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/download/report',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Stream a generated report file
     * Return the generated report file as a binary download.
     * @returns any Successful Response
     * @throws ApiError
     */
    public static downloadFileDownloadFileReportIdGet({
        reportId,
    }: {
        reportId: string,
    }): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/download/file/{report_id}',
            path: {
                'report_id': reportId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
}
