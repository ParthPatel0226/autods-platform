/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { EDAQuestionOption } from './EDAQuestionOption';
export type EDAQuestion = {
    id: string;
    step?: string;
    question: string;
    type: string;
    options?: Array<EDAQuestionOption>;
    recommendation_reason?: (string | null);
    domain_specific?: boolean;
};

