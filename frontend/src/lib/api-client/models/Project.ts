/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export type Project = {
    project_id: string;
    name: string;
    user_mode?: string;
    detected_domain?: (string | null);
    target_column?: (string | null);
    problem_type?: (string | null);
    current_step?: (string | null);
    completed_steps?: Array<string>;
    created_at: string;
    updated_at: string;
};

