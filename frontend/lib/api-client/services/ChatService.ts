/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ChatHistory } from '../models/ChatHistory';
import type { ChatResponse } from '../models/ChatResponse';
import type { ChatSendRequest } from '../models/ChatSendRequest';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class ChatService {
    /**
     * Send a follow-up message in the project conversation
     * Dispatch message to the follow-up agent and return the assistant reply.
     * @returns ChatResponse Successful Response
     * @throws ApiError
     */
    public static sendMessageChatMessagePost({
        requestBody,
    }: {
        requestBody: ChatSendRequest,
    }): CancelablePromise<ChatResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/chat/message',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Retrieve full chat history for a project
     * Return all chat messages exchanged in the project session.
     * @returns ChatHistory Successful Response
     * @throws ApiError
     */
    public static getHistoryChatHistoryProjectIdGet({
        projectId,
    }: {
        projectId: string,
    }): CancelablePromise<ChatHistory> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/chat/history/{project_id}',
            path: {
                'project_id': projectId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Clear chat history for a project
     * Wipe all chat messages from the project session.
     * @returns any Successful Response
     * @throws ApiError
     */
    public static clearHistoryChatHistoryProjectIdDelete({
        projectId,
    }: {
        projectId: string,
    }): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'DELETE',
            url: '/chat/history/{project_id}',
            path: {
                'project_id': projectId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
}
