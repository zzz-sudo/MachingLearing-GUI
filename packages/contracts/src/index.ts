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

export type WorkspaceError = {
  errorType: string;
  message: string;
  operation: string;
  recoverable: boolean;
  details: Record<string, unknown>;
};

