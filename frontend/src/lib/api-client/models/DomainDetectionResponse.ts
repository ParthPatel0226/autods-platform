/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { DomainAlternative } from './DomainAlternative';
export type DomainDetectionResponse = {
    detected_domain: string;
    confidence: number;
    evidence: Array<string>;
    alternatives: Array<DomainAlternative>;
};

