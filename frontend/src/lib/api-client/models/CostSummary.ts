/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export type CostSummary = {
    api_call_count: number;
    api_token_count: number;
    step_breakdown: Array<Record<string, any>>;
    current_step?: (string | null);
    completed_steps?: Array<string>;
};

