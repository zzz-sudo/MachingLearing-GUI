import type { Job, Project } from "@ml-gui/contracts";

const now = new Date();

export const demoProjects: Project[] = [
  {
    id: "project-sales-east",
    name: "销售预测项目",
    path: "D:\\MLWorkspace\\销售预测项目",
    createdAt: new Date(now.getTime() - 86_400_000 * 8).toISOString(),
    updatedAt: now.toISOString(),
  },
];

export const demoJobs: Job[] = [
  {
    id: "job-training-001",
    projectId: "project-sales-east",
    title: "训练销量回归模型",
    status: "running",
    progress: 68,
    message: "正在训练 HistGradientBoosting 模型并计算验证指标。",
    createdAt: new Date(now.getTime() - 1_020_000).toISOString(),
    updatedAt: new Date(now.getTime() - 30_000).toISOString(),
  },
  {
    id: "job-profile-001",
    projectId: "project-sales-east",
    title: "检查销售数据字段",
    status: "succeeded",
    progress: 100,
    message: "字段检查已完成，发现 2 个需要确认的日期字段。",
    createdAt: new Date(now.getTime() - 5_400_000).toISOString(),
    updatedAt: new Date(now.getTime() - 4_800_000).toISOString(),
  },
  {
    id: "job-document-001",
    projectId: "project-sales-east",
    title: "解析字段说明 PDF",
    status: "waiting_confirmation",
    progress: 100,
    message: "已提取 3 个表格，等待确认字段映射。",
    createdAt: new Date(now.getTime() - 9_800_000).toISOString(),
    updatedAt: new Date(now.getTime() - 8_400_000).toISOString(),
  },
];

