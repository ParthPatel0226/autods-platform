/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export type JobStatus = {
    job_id: string;
    status: string;
    progress?: number;
    current_step?: (string | null);
    started_at: string;
    finished_at?: (string | null);
    error?: (string | null);
};

