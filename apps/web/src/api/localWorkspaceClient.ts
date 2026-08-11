import type { ServiceHealth } from "@ml-gui/contracts";

const DEFAULT_API_BASE_URL = "http://127.0.0.1:8765/api";

export class LocalWorkspaceClient {
  constructor(private readonly baseUrl = DEFAULT_API_BASE_URL) {}

  async getHealth(): Promise<ServiceHealth> {
    const response = await fetch(`${this.baseUrl}/health`);
    if (!response.ok) {
      throw new Error(`本地任务服务返回 HTTP ${response.status}`);
    }

    return (await response.json()) as ServiceHealth;
  }
}

