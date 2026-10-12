import { apiClient } from './api-client';
import type {
  RippleBrainAction,
  RippleBrainAnalysis,
  RippleBrainRun,
} from '@app-starter/shared';

export interface AnalyzeRippleBrainRequest {
  changeRequest: string;
}

export interface RippleBrainDecisionRequest {
  note?: string;
}

export interface RippleBrainRunListResponse {
  items: RippleBrainRun[];
  total: number;
}

export class RippleBrainApi {
  async analyze(organizationId: string, data: AnalyzeRippleBrainRequest): Promise<RippleBrainAnalysis> {
    return apiClient.post<RippleBrainAnalysis>(
      `/api/organizations/${organizationId}/ripplebrain/analyze`,
      data,
    );
  }

  async approve(
    organizationId: string,
    actionId: string,
    data: RippleBrainDecisionRequest,
  ): Promise<RippleBrainAction> {
    return apiClient.post<RippleBrainAction>(
      `/api/organizations/${organizationId}/ripplebrain/actions/${actionId}/approve`,
      data,
    );
  }

  async reject(
    organizationId: string,
    actionId: string,
    data: RippleBrainDecisionRequest,
  ): Promise<RippleBrainAction> {
    return apiClient.post<RippleBrainAction>(
      `/api/organizations/${organizationId}/ripplebrain/actions/${actionId}/reject`,
      data,
    );
  }

  async listRuns(organizationId: string): Promise<RippleBrainRunListResponse> {
    return apiClient.get<RippleBrainRunListResponse>(
      `/api/organizations/${organizationId}/ripplebrain/runs`,
    );
  }
}

export const rippleBrainApi = new RippleBrainApi();
