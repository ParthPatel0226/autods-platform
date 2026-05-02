/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ConfidenceInterval } from './ConfidenceInterval';
export type PredictResponse = {
    prediction: any;
    probability?: (number | null);
    confidence_interval?: (ConfidenceInterval | null);
    shap?: (Record<string, number> | null);
};

