import type {
  AlgorithmCatalog,
  ChartSpec,
  ChartSpecCreate,
  ChartGenerationResult,
  Asset,
  DatasetColumnSpec,
  DatasetVersion,
  DocumentParseResult,
  ImportResult,
  Project,
  ProjectFileNode,
  ServiceHealth,
  TablePreview,
  Job,
  TrainingCreate,
  TrainingResult,
  WorkspaceError,
} from "@ml-gui/contracts";

const DEFAULT_API_BASE_URL = "http://127.0.0.1:8765/api";

export class LocalWorkspaceClient {
  getAlgorithmCatalog(): Promise<AlgorithmCatalog> {
    return this.request<AlgorithmCatalog>("/algorithms");
  }

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

  async getProjectTree(projectId: string, includeHidden: boolean): Promise<ProjectFileNode[]> {
    return this.request<ProjectFileNode[]>(
      `/projects/${projectId}/tree?includeHidden=${String(includeHidden)}`,
    );
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

  async listCharts(projectId: string): Promise<ChartSpec[]> {
    return this.request<ChartSpec[]>(`/projects/${projectId}/charts`);
  }

  async createChart(projectId: string, payload: ChartSpecCreate): Promise<ChartSpec> {
    return this.request<ChartSpec>(`/projects/${projectId}/charts`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
  }

  async getChart(chartId: string): Promise<ChartSpec> {
    return this.request<ChartSpec>(`/charts/${chartId}`);
  }

  async generateChart(projectId: string, chartId: string): Promise<ChartGenerationResult> {
    return this.request<ChartGenerationResult>(`/projects/${projectId}/charts/${chartId}/generate`, { method: "POST" });
  }

  async getChartResult(jobId: string): Promise<ChartGenerationResult> {
    return this.request<ChartGenerationResult>(`/jobs/${jobId}/chart-result`);
  }

  getChartArtifactUrl(jobId: string, relativePath: string): string {
    const encodedPath = relativePath.split("/").map((part) => encodeURIComponent(part)).join("/");
    return `${this.baseUrl}/jobs/${jobId}/chart-artifacts/${encodedPath}`;
  }

  async listJobs(projectId: string): Promise<Job[]> {
    return this.request<Job[]>(`/jobs?projectId=${encodeURIComponent(projectId)}`);
  }

  async createTraining(projectId: string, payload: TrainingCreate): Promise<TrainingResult> {
    return this.request<TrainingResult>(`/projects/${projectId}/training`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
  }

  async getTrainingResult(jobId: string): Promise<TrainingResult> {
    return this.request<TrainingResult>(`/jobs/${jobId}/training-result`);
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

  getAssetContentUrl(assetId: string): string {
    return `${this.baseUrl}/assets/${assetId}/content`;
  }

  getProjectFileContentUrl(projectId: string, relativePath: string): string {
    const query = new URLSearchParams({ path: relativePath });
    return `${this.baseUrl}/projects/${projectId}/files/content?${query.toString()}`;
  }

  getDocumentExportUrl(assetId: string, outputFormat: "docx" | "xlsx" | "md" | "txt"): string {
    return `${this.baseUrl}/assets/${assetId}/document/export?format=${outputFormat}`;
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
