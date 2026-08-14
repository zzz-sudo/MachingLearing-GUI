export type JobStatus =
  | "queued"
  | "running"
  | "waiting_confirmation"
  | "succeeded"
  | "failed"
  | "cancelled";

export type Project = {
  id: string;
  name: string;
  path: string;
  createdAt: string;
  updatedAt: string;
};

export type Job = {
  id: string;
  projectId: string;
  title: string;
  status: JobStatus;
  progress: number;
  createdAt: string;
  updatedAt: string;
  message?: string;
};

export type ServiceHealth = {
  status: "ready";
  service: string;
  version: string;
};

export type Asset = {
  id: string;
  projectId: string;
  name: string;
  relativePath: string;
  mediaType: string;
  size: number;
  sha256: string;
  parentAssetId?: string | null;
  createdAt: string;
};

export type PreviewColumn = {
  name: string;
  inferredType: "empty" | "boolean" | "integer" | "number" | "text";
  nullCount: number;
};

export type TablePreview = {
  assetId: string;
  sourceName: string;
  format: "csv" | "xlsx";
  encoding?: string | null;
  sheetName?: string | null;
  rowCount: number;
  columnCount: number;
  columns: PreviewColumn[];
  rows: Array<Record<string, unknown>>;
};

export type ImportResult = {
  importedAssets: Asset[];
  preview?: TablePreview | null;
  extractedCount: number;
  warnings: string[];
};

export type DatasetColumnSpec = {
  name: string;
  dataType: "text" | "integer" | "number" | "boolean";
};

export type DatasetVersion = {
  id: string;
  projectId: string;
  sourceAssetId: string;
  version: number;
  parquetRelativePath: string;
  rowCount: number;
  columns: DatasetColumnSpec[];
  createdAt: string;
};

export type WorkspaceError = {
  errorType: string;
  message: string;
  operation: string;
  recoverable: boolean;
  details: Record<string, unknown>;
};
