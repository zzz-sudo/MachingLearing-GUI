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

export type TrainingCreate = {
  datasetId: string;
  method?: "classification" | "regression" | "anova" | "clustering" | "deep-learning" | null;
  taskType?: string | null;
  algorithmId?: string | null;
  targetColumn?: string | null;
  featureColumns?: string[];
  factorColumns?: string[];
  timeColumn?: string | null;
  groupColumn?: string | null;
  validationRatio: number;
  testRatio?: number;
  randomSeed: number;
  computeMode: "auto" | "cpu" | "gpu";
  parameters?: Record<string, boolean | number | string>;
};

export type TrainingArtifact = {
  kind: string;
  relativePath: string;
  mediaType: string;
  description: string;
};

export type TrainingResult = {
  jobId: string;
  method: string;
  taskType?: string | null;
  algorithmId?: string | null;
  status: JobStatus;
  targetColumn?: string | null;
  featureColumns: string[];
  parameters: Record<string, boolean | number | string>;
  metrics: Record<string, number>;
  tables: Record<string, Array<Record<string, unknown>>>;
  artifacts: TrainingArtifact[];
  warnings: string[];
  environment: Record<string, string>;
  artifactRelativePath?: string | null;
  errorType?: string | null;
  errorMessage?: string | null;
};

export type AlgorithmTaskType =
  | "classification"
  | "regression"
  | "clustering"
  | "anova"
  | "sequence_regression"
  | "sequence_classification";

export type AlgorithmParameter = {
  id: string;
  label: string;
  valueType: "integer" | "number" | "boolean" | "select";
  default: number | boolean | string;
  minimum?: number | null;
  maximum?: number | null;
  step?: number | null;
  options: string[];
  description: string;
};

export type AlgorithmDefinition = {
  id: string;
  name: string;
  taskType: AlgorithmTaskType;
  family: string;
  description: string;
  requiresTarget: boolean;
  requiresFactors: boolean;
  requiresTime: boolean;
  supportsGpu: boolean;
  parameters: AlgorithmParameter[];
};

export type AlgorithmCatalog = {
  version: number;
  algorithms: AlgorithmDefinition[];
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

export type ProjectFileNode = {
  name: string;
  relativePath: string;
  kind: "directory" | "file";
  hidden: boolean;
  size?: number | null;
  assetId?: string | null;
  children: ProjectFileNode[];
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

export type DocumentParseResult = {
  assetId: string;
  pdfType: "text_based" | "scanned" | "image_based" | "mixed";
  engine: string;
  status: "parsed" | "partial" | "ocr_required";
  pageCount: number;
  ocrPages: number[];
  pagesNeedingOcr: number[];
  markdownRelativePath?: string | null;
  jsonRelativePath: string;
  markdownPreview: string;
  pages: Array<{ pageNumber: number; text: string; needsOcr: boolean }>;
};

export type ImportResult = {
  importedAssets: Asset[];
  preview?: TablePreview | null;
  document?: DocumentParseResult | null;
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
