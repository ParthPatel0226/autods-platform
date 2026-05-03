/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { JoinKey } from './JoinKey';
export type JoinPlan = {
    left_source_id: string;
    right_source_id: string;
    join_keys: Array<JoinKey>;
    join_type?: 'inner' | 'left' | 'right' | 'outer';
};

