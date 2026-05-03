/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { CreateProjectRequest } from '../models/CreateProjectRequest';
import type { Project } from '../models/Project';
import type { ProjectListItem } from '../models/ProjectListItem';
import type { UpdateProjectRequest } from '../models/UpdateProjectRequest';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class ProjectsService {
    /**
     * List Projects
     * List all projects owned by the current user.
     * @returns ProjectListItem Successful Response
     * @throws ApiError
     */
    public static listProjectsProjectsGet(): CancelablePromise<Array<ProjectListItem>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/projects/',
        });
    }
    /**
     * Create Project
     * Create a new project (analysis session).
     * @returns Project Successful Response
     * @throws ApiError
     */
    public static createProjectProjectsPost({
        requestBody,
    }: {
        requestBody: CreateProjectRequest,
    }): CancelablePromise<Project> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/projects/',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Get Project
     * Return full state for a project.
     * @returns Project Successful Response
     * @throws ApiError
     */
    public static getProjectProjectsProjectIdGet({
        projectId,
    }: {
        projectId: string,
    }): CancelablePromise<Project> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/projects/{project_id}',
            path: {
                'project_id': projectId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Update Project
     * Patch project metadata (name, description).
     * @returns Project Successful Response
     * @throws ApiError
     */
    public static updateProjectProjectsProjectIdPatch({
        projectId,
        requestBody,
    }: {
        projectId: string,
        requestBody: UpdateProjectRequest,
    }): CancelablePromise<Project> {
        return __request(OpenAPI, {
            method: 'PATCH',
            url: '/projects/{project_id}',
            path: {
                'project_id': projectId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Delete Project
     * Permanently delete a project and all its state.
     * @returns any Successful Response
     * @throws ApiError
     */
    public static deleteProjectProjectsProjectIdDelete({
        projectId,
    }: {
        projectId: string,
    }): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'DELETE',
            url: '/projects/{project_id}',
            path: {
                'project_id': projectId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Activate Project
     * Mark a project as the active session (sets workflow_status=active).
     * @returns any Successful Response
     * @throws ApiError
     */
    public static activateProjectProjectsProjectIdActivatePost({
        projectId,
    }: {
        projectId: string,
    }): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/projects/{project_id}/activate',
            path: {
                'project_id': projectId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
}
