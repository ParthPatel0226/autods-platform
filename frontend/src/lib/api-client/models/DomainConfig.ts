/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export type DomainConfig = {
    domain_name: string;
    display_name: string;
    icon?: (string | null);
    primary_metrics?: Record<string, Array<string>>;
    eda_questions?: Array<Record<string, any>>;
    feature_questions?: Array<Record<string, any>>;
    model_questions?: Array<Record<string, any>>;
    fairness?: (Record<string, any> | null);
    compliance_notes?: Array<string>;
    report_style?: (string | null);
};

