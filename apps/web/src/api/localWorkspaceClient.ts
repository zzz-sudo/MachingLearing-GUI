import type {
  Asset,
  DatasetColumnSpec,
  DatasetVersion,
  DocumentParseResult,
  ImportResult,
  Project,
  ServiceHealth,
  TablePreview,
  WorkspaceError,
} from "@ml-gui/contracts";

const DEFAULT_API_BASE_URL = "http://127.0.0.1:8765/api";

export class LocalWorkspaceClient {
  constructor(private readonly baseUrl = DEFAULT_API_BASE_URL) {}

  async getHealth(): Promise<ServiceHealth> {
    return this.request<ServiceHealth>("/health");
  }

  async getDefaultProject(): Promise<Project> {
    return this.request<Project>("/projects/default", { method: "POST" });
  }

  async listAssets(projectId: string): Promise<Asset[]> {
    return this.request<Asset[]>(`/projects/${projectId}/assets`);
  }

  async getPreview(assetId: string): Promise<TablePreview> {
    return this.request<TablePreview>(`/assets/${assetId}/preview`);
  }

  async getDocument(assetId: string): Promise<DocumentParseResult> {
    return this.request<DocumentParseResult>(`/assets/${assetId}/document`);
  }

  async listDatasets(projectId: string): Promise<DatasetVersion[]> {
    return this.request<DatasetVersion[]>(`/projects/${projectId}/datasets`);
  }

  async createDataset(
    projectId: string,
    assetId: string,
    columns: DatasetColumnSpec[],
  ): Promise<DatasetVersion> {
    return this.request<DatasetVersion>(`/projects/${projectId}/datasets`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ assetId, columns }),
    });
  }

  getParquetUrl(datasetId: string): string {
    return `${this.baseUrl}/datasets/${datasetId}/parquet`;
  }

  async importFile(projectId: string, file: File): Promise<ImportResult> {
    return this.request<ImportResult>(`/projects/${projectId}/imports`, {
      method: "POST",
      headers: {
        "Content-Type": "application/octet-stream",
        "X-Filename": encodeURIComponent(file.name),
      },
      body: await file.arrayBuffer(),
    });
  }

  private async request<T>(path: string, init?: RequestInit): Promise<T> {
    const response = await fetch(`${this.baseUrl}${path}`, init);
    if (!response.ok) {
      const payload = (await response.json().catch(() => null)) as WorkspaceError | null;
      if (payload?.errorType) {
        throw new WorkspaceClientError(payload);
      }
      throw new Error(`本地任务服务返回 HTTP ${response.status}`);
    }
    return (await response.json()) as T;
  }
}

export class WorkspaceClientError extends Error {
  constructor(readonly workspaceError: WorkspaceError) {
    super(workspaceError.message);
    this.name = workspaceError.errorType;
  }
}
