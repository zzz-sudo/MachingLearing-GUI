import { useEffect, useMemo, useRef, useState } from "react";
import type { ReactNode } from "react";
import type {
  Asset,
  DatasetColumnSpec,
  DatasetVersion,
  DocumentParseResult,
  Job,
  Project,
  ProjectFileNode,
  ServiceHealth,
  TablePreview,
  WorkspaceError,
  TrainingCreate,
  TrainingResult,
} from "@ml-gui/contracts";
import {
  Archive,
  BarChart3,
  Bot,
  Box,
  Braces,
  ChevronDown,
  ChevronRight,
  CircleStop,
  Database,
  Download,
  Eye,
  EyeOff,
  File as FileIcon,
  FileDown,
  FileSpreadsheet,
  FileText,
  Folder,
  FolderOpen,
  History,
  Import,
  LayoutDashboard,
  Layers3,
  LineChart,
  ListTree,
  MessageSquareText,
  Network,
  PanelRightClose,
  Play,
  Search,
  Settings,
  SlidersHorizontal,
  Sparkles,
  Sigma,
  Wrench,
  X,
} from "lucide-react";
import {
  Panel,
  PanelGroup,
  PanelResizeHandle,
} from "react-resizable-panels";
import {
  LocalWorkspaceClient,
  WorkspaceClientError,
} from "./api/localWorkspaceClient";
import { demoProjects } from "./data/demo";

const workspaceClient = new LocalWorkspaceClient();
const initialProject = demoProjects[0]!;

const railItems = [
  { id: "workspace", label: "工作台", icon: LayoutDashboard },
  { id: "datasets", label: "数据", icon: Database },
  { id: "documents", label: "文档", icon: FileText },
  { id: "models", label: "模型", icon: Box },
  { id: "jobs", label: "任务", icon: History },
  { id: "tools", label: "工具", icon: Wrench },
] as const;

const analysisMethods = [
  { id: "classification", label: "分类", group: "监督学习", detail: "预测离散类别", icon: Layers3 },
  { id: "regression", label: "回归", group: "监督学习", detail: "预测连续数值", icon: LineChart },
  { id: "anova", label: "方差分析", group: "统计分析", detail: "比较组间差异", icon: Sigma },
  { id: "clustering", label: "聚类", group: "无监督学习", detail: "发现样本分组", icon: Network },
  { id: "deep-learning", label: "深度学习", group: "神经网络", detail: "配置多层网络", icon: Sparkles },
] as const;

const statusLabels: Record<Job["status"], string> = {
  queued: "排队中",
  running: "运行中",
  waiting_confirmation: "等待确认",
  succeeded: "已完成",
  failed: "失败",
  cancelled: "已取消",
};

export function App() {
  const [activeRail, setActiveRail] = useState("workspace");
  const [activeInspector, setActiveInspector] = useState("properties");
  const [activeMode, setActiveMode] = useState("task");
  const [selectedJobId, setSelectedJobId] = useState<string | null>(null);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [trainingResult, setTrainingResult] = useState<TrainingResult | null>(null);
  const [prompt, setPrompt] = useState("");
  const [health, setHealth] = useState<ServiceHealth | null>(null);
  const [serviceError, setServiceError] = useState<string | null>(null);
  const [selectedProject, setSelectedProject] = useState(initialProject);
  const [projectReady, setProjectReady] = useState(false);
  const [assets, setAssets] = useState<Asset[]>([]);
  const [fileTree, setFileTree] = useState<ProjectFileNode[]>([]);
  const [showHidden, setShowHidden] = useState(true);
  const [selectedAsset, setSelectedAsset] = useState<Asset | null>(null);
  const [selectedFilePath, setSelectedFilePath] = useState<string | null>(null);
  const [preview, setPreview] = useState<TablePreview | null>(null);
  const [dataset, setDataset] = useState<DatasetVersion | null>(null);
  const [documentResult, setDocumentResult] = useState<DocumentParseResult | null>(null);
  const [fieldTypes, setFieldTypes] = useState<Record<string, DatasetColumnSpec["dataType"]>>({});
  const [confirming, setConfirming] = useState(false);
  const [importing, setImporting] = useState(false);
  const [importError, setImportError] = useState<WorkspaceError | null>(null);
  const [updateCenterOpen, setUpdateCenterOpen] = useState(false);
  const [inspectorVisible, setInspectorVisible] = useState(true);
  const [selectedAnalysis, setSelectedAnalysis] = useState("regression");
  const [modelPlanStatus, setModelPlanStatus] = useState("尚未创建分析计划");
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    void workspaceClient
      .getHealth()
      .then((result) => {
        setHealth(result);
        setServiceError(null);
      })
      .catch((error: unknown) => {
        setHealth(null);
        setServiceError(
          error instanceof Error ? error.message : "本地任务服务连接失败",
        );
      });

    void workspaceClient
      .getDefaultProject()
      .then(async (project) => {
        setSelectedProject(project);
        const projectAssets = await workspaceClient.listAssets(project.id);
        setAssets(projectAssets);
        setFileTree(await workspaceClient.getProjectTree(project.id, true));
        const datasets = await workspaceClient.listDatasets(project.id);
        setDataset(datasets[0] ?? null);
        const projectJobs = await workspaceClient.listJobs(project.id);
        setJobs(projectJobs);
        setSelectedJobId(projectJobs[0]?.id ?? null);
        for (const asset of projectAssets) {
          if (asset.name.toLowerCase().endsWith(".pdf")) {
            try {
              setDocumentResult(await workspaceClient.getDocument(asset.id));
              setSelectedAsset(asset);
              setSelectedFilePath(asset.relativePath);
              setPreview(null);
              break;
            } catch {
              // PDF assets without completed classification are skipped.
            }
          }
          try {
            const restoredPreview = await workspaceClient.getPreview(asset.id);
            setPreview(restoredPreview);
            setSelectedAsset(asset);
            setSelectedFilePath(asset.relativePath);
            setFieldTypes(createInitialFieldTypes(restoredPreview));
            break;
          } catch {
            // Assets without table previews are skipped during workspace restoration.
          }
        }
        setProjectReady(true);
      })
      .catch((error: unknown) => {
        setServiceError(error instanceof Error ? error.message : "无法打开本地工作区");
      });
  }, []);

  useEffect(() => {
    if (!projectReady) {
      return;
    }
    void workspaceClient
      .getProjectTree(selectedProject.id, showHidden)
      .then(setFileTree)
      .catch((error: unknown) => {
        setServiceError(error instanceof Error ? error.message : "无法读取项目文件树");
      });
  }, [projectReady, selectedProject.id, showHidden]);

  useEffect(() => {
    if (!projectReady) {
      return;
    }
    const refreshJobs = () => void workspaceClient.listJobs(selectedProject.id)
      .then((nextJobs) => {
        setJobs(nextJobs);
        setSelectedJobId((current) => current ?? nextJobs[0]?.id ?? null);
      })
      .catch(() => undefined);
    refreshJobs();
    const timer = window.setInterval(refreshJobs, 2000);
    return () => window.clearInterval(timer);
  }, [projectReady, selectedProject.id]);

  const selectedJob = useMemo(
    () => jobs.find((job) => job.id === selectedJobId) ?? null,
    [jobs, selectedJobId],
  );
  const selectedProjectFile = useMemo(
    () => selectedFilePath ? findProjectFile(fileTree, selectedFilePath) : null,
    [fileTree, selectedFilePath],
  );

  useEffect(() => {
    if (!selectedJob || !["succeeded", "failed"].includes(selectedJob.status)) {
      return;
    }
    void workspaceClient.getTrainingResult(selectedJob.id).then(setTrainingResult).catch(() => undefined);
  }, [selectedJob?.id, selectedJob?.status]);

  async function importSelectedFile(file: File) {
    if (!projectReady) {
      return;
    }
    setImporting(true);
    setImportError(null);
    try {
      const result = await workspaceClient.importFile(selectedProject.id, file);
      setPreview(result.preview ?? null);
      setDocumentResult(result.document ?? null);
      setDataset(null);
      setFieldTypes(result.preview ? createInitialFieldTypes(result.preview) : {});
      const projectAssets = await workspaceClient.listAssets(selectedProject.id);
      setAssets(projectAssets);
      setFileTree(await workspaceClient.getProjectTree(selectedProject.id, showHidden));
      const importedAssetId = result.document?.assetId ?? result.preview?.assetId;
      const importedAsset = projectAssets.find((asset) => asset.id === importedAssetId) ?? null;
      setSelectedAsset(importedAsset);
      setSelectedFilePath(importedAsset?.relativePath ?? null);
      setActiveRail(result.document ? "documents" : "datasets");
      setActiveInspector("properties");
    } catch (error: unknown) {
      if (error instanceof WorkspaceClientError) {
        setImportError(error.workspaceError);
      } else {
        setImportError({
          errorType: "LocalServiceError",
          message: error instanceof Error ? error.message : "文件导入失败",
          operation: "file_import",
          recoverable: true,
          details: {},
        });
      }
    } finally {
      setImporting(false);
    }
  }

  async function openAsset(assetId: string) {
    const asset = assets.find((item) => item.id === assetId);
    if (!asset) {
      return;
    }
    setSelectedAsset(asset);
    setSelectedFilePath(asset.relativePath);
    setImportError(null);
    if (asset.name.toLowerCase().endsWith(".pdf")) {
      try {
        setDocumentResult(await workspaceClient.getDocument(assetId));
        setPreview(null);
        setActiveRail("documents");
      } catch (error: unknown) {
        setImportError(asWorkspaceError(error, "document_open", "无法打开文档解析结果"));
      }
      return;
    }
    if (isTextPreviewFile(asset.name)) {
      setPreview(null);
      setDocumentResult(null);
      setActiveRail("documents");
      return;
    }
    try {
      const restoredPreview = await workspaceClient.getPreview(assetId);
      setPreview(restoredPreview);
      setDocumentResult(null);
      setFieldTypes(createInitialFieldTypes(restoredPreview));
      setActiveRail("datasets");
    } catch (error: unknown) {
      setImportError(asWorkspaceError(error, "asset_open", "当前文件没有可用预览"));
    }
  }

  function openProjectFile(file: ProjectFileNode) {
    setSelectedFilePath(file.relativePath);
    if (file.assetId) {
      void openAsset(file.assetId);
      return;
    }
    setSelectedAsset(null);
    setPreview(null);
    setDocumentResult(null);
    setImportError(null);
    setActiveRail("documents");
  }

  async function confirmFields() {
    if (!preview) {
      return;
    }
    setConfirming(true);
    setImportError(null);
    try {
      const columns = preview.columns.map((column) => ({
        name: column.name,
        dataType: fieldTypes[column.name] ?? "text",
      }));
      setDataset(await workspaceClient.createDataset(selectedProject.id, preview.assetId, columns));
    } catch (error: unknown) {
      const workspaceError = error instanceof WorkspaceClientError
        ? error.workspaceError
        : { errorType: "DatasetCreateError", message: error instanceof Error ? error.message : "数据集创建失败", operation: "dataset_create", recoverable: true, details: {} };
      setImportError(workspaceError);
    } finally {
      setConfirming(false);
    }
  }

  async function createTraining(payload: TrainingCreate) {
    try {
      const result = await workspaceClient.createTraining(selectedProject.id, payload);
      setTrainingResult(result);
      setModelPlanStatus("训练任务已提交给本地 Worker");
      const nextJobs = await workspaceClient.listJobs(selectedProject.id);
      setJobs(nextJobs);
      setSelectedJobId(result.jobId);
    } catch (error: unknown) {
      setImportError(asWorkspaceError(error, "training_create", "无法创建训练任务"));
    }
  }

  function submitPrompt() {
    const message = prompt.trim();
    if (!message) {
      return;
    }

    setPrompt("");
  }

  return (
    <div className="app-shell">
      <input
        ref={fileInputRef}
        className="sr-only"
        type="file"
        accept=".csv,.xlsx,.pdf,.zip,.tar,.tgz,.gz"
        onChange={(event) => {
          const file = event.target.files?.[0];
          if (file) {
            void importSelectedFile(file);
          }
          event.target.value = "";
        }}
      />
      <GlobalRail
        activeItem={activeRail}
        onChange={setActiveRail}
        onOpenUpdateCenter={() => setUpdateCenterOpen(true)}
      />

      <PanelGroup direction="horizontal" className="workspace-panels">
        <Panel defaultSize={19} minSize={15} maxSize={28}>
          <ContextSidebar
            activeRail={activeRail}
            jobs={jobs}
            project={selectedProject}
            assets={assets}
            fileTree={fileTree}
            showHidden={showHidden}
            importing={importing}
            projectReady={projectReady}
            selectedJobId={selectedJobId}
            selectedFilePath={selectedFilePath}
            selectedAnalysis={selectedAnalysis}
            onImport={() => projectReady && fileInputRef.current?.click()}
            onSelectAnalysis={(analysis) => {
              setSelectedAnalysis(analysis);
              setActiveRail("models");
            }}
            onSelectFile={openProjectFile}
            onSelectJob={setSelectedJobId}
            onShowHiddenChange={setShowHidden}
          />
        </Panel>

        <ResizeHandle />

        <Panel defaultSize={56} minSize={40}>
          <main className="main-workspace">
            <WorkspaceHeader
              activeRail={activeRail}
              health={health}
              preview={preview}
              project={selectedProject}
              serviceError={serviceError}
              selectedAsset={selectedAsset}
              selectedFile={selectedProjectFile}
              inspectorVisible={inspectorVisible}
              onToggleInspector={() => setInspectorVisible((current) => !current)}
            />
            <WorkflowBar activeRail={activeRail} job={selectedJob} preview={preview} />
            <WorkspaceContent
              activeRail={activeRail}
              job={selectedJob}
              project={selectedProject}
              preview={preview}
              importError={importError}
              importing={importing}
              confirming={confirming}
              dataset={dataset}
              documentResult={documentResult}
              selectedAsset={selectedAsset}
              selectedFile={selectedProjectFile}
              selectedAnalysis={selectedAnalysis}
              modelPlanStatus={modelPlanStatus}
              jobs={jobs}
              trainingResult={trainingResult}
              projectReady={projectReady}
              onConfirm={() => void confirmFields()}
              onExport={() => dataset && window.open(workspaceClient.getParquetUrl(dataset.id), "_blank")}
              onImport={() => projectReady && fileInputRef.current?.click()}
              onSelectAnalysis={setSelectedAnalysis}
              onCreateModelPlan={createTraining}
            />
            <CommandDock
              activeMode={activeMode}
              prompt={prompt}
              onModeChange={setActiveMode}
              onPromptChange={setPrompt}
              onSubmit={submitPrompt}
            />
          </main>
        </Panel>

        {inspectorVisible ? <ResizeHandle /> : null}

        {inspectorVisible ? <Panel defaultSize={25} minSize={20} maxSize={34} collapsible>
          <InspectorPanel
            activeRail={activeRail}
            activeTab={activeInspector}
            job={selectedJob}
            project={selectedProject}
            preview={preview}
            dataset={dataset}
            documentResult={documentResult}
            selectedAsset={selectedAsset}
            selectedFile={selectedProjectFile}
            selectedAnalysis={selectedAnalysis}
            fieldTypes={fieldTypes}
            onFieldTypeChange={(name, dataType) => setFieldTypes((current) => ({ ...current, [name]: dataType }))}
            onTabChange={setActiveInspector}
          />
        </Panel> : null}
      </PanelGroup>
      {updateCenterOpen ? <UpdateCenter onClose={() => setUpdateCenterOpen(false)} /> : null}
    </div>
  );
}

type GlobalRailProps = {
  activeItem: string;
  onChange: (item: string) => void;
  onOpenUpdateCenter: () => void;
};

function GlobalRail({ activeItem, onChange, onOpenUpdateCenter }: GlobalRailProps) {
  return (
    <nav className="global-rail" aria-label="全局导航">
      <button className="brand-button" title="MachingLearing GUI" type="button">
        ML
      </button>

      <div className="rail-actions">
        {railItems.map((item) => {
          const Icon = item.icon;
          return (
            <button
              key={item.id}
              className="rail-button"
              data-active={activeItem === item.id}
              title={item.label}
              type="button"
              onClick={() => onChange(item.id)}
            >
              <Icon aria-hidden="true" size={19} strokeWidth={1.8} />
              <span className="sr-only">{item.label}</span>
            </button>
          );
        })}
      </div>

      <button
        className="rail-button rail-settings"
        title="设置和版本升级"
        type="button"
        onClick={onOpenUpdateCenter}
      >
        <Settings aria-hidden="true" size={19} strokeWidth={1.8} />
        <span className="sr-only">设置和版本升级</span>
      </button>
    </nav>
  );
}

type UpdateStatus = "idle" | "checking" | "available" | "current" | "installing" | "error";

function UpdateCenter({ onClose }: { onClose: () => void }) {
  const [applicationVersion, setApplicationVersion] = useState("Web 预览");
  const [availableVersion, setAvailableVersion] = useState<string | null>(null);
  const [status, setStatus] = useState<UpdateStatus>("idle");
  const [message, setMessage] = useState("尚未检查更新");
  const pendingUpdate = useRef<{
    version: string;
    downloadAndInstall: () => Promise<void>;
  } | null>(null);

  useEffect(() => {
    if (!("__TAURI_INTERNALS__" in window)) {
      return;
    }
    void import("@tauri-apps/api/app")
      .then(({ getVersion }) => getVersion())
      .then(setApplicationVersion)
      .catch((error: unknown) => {
        setStatus("error");
        setMessage(error instanceof Error ? error.message : "无法读取应用版本");
      });
  }, []);

  async function checkForUpdate() {
    if (!("__TAURI_INTERNALS__" in window)) {
      setStatus("error");
      setMessage("Web 预览不执行桌面升级，请在 Windows 桌面应用中检查");
      return;
    }
    setStatus("checking");
    setMessage("正在连接 GitHub Release");
    try {
      const { check } = await import("@tauri-apps/plugin-updater");
      const update = await check();
      pendingUpdate.current = update;
      if (update) {
        setAvailableVersion(update.version);
        setStatus("available");
        setMessage(`发现版本 ${update.version}`);
      } else {
        setAvailableVersion(null);
        setStatus("current");
        setMessage("当前已经是最新版本");
      }
    } catch (error: unknown) {
      setStatus("error");
      setMessage(error instanceof Error ? error.message : "更新检查失败");
    }
  }

  async function installUpdate() {
    const update = pendingUpdate.current;
    if (!update) {
      return;
    }
    setStatus("installing");
    setMessage("正在下载并安装更新");
    try {
      await update.downloadAndInstall();
      const { relaunch } = await import("@tauri-apps/plugin-process");
      await relaunch();
    } catch (error: unknown) {
      setStatus("error");
      setMessage(error instanceof Error ? error.message : "更新安装失败");
    }
  }

  return (
    <div className="update-overlay" role="presentation" onMouseDown={onClose}>
      <section
        aria-labelledby="update-center-title"
        aria-modal="true"
        className="update-dialog"
        role="dialog"
        onMouseDown={(event) => event.stopPropagation()}
      >
        <header className="update-dialog-header">
          <div>
            <span className="section-kicker">桌面应用</span>
            <h2 id="update-center-title">版本升级</h2>
          </div>
          <button className="icon-button" title="关闭" type="button" onClick={onClose}>
            <X aria-hidden="true" size={17} />
            <span className="sr-only">关闭</span>
          </button>
        </header>
        <div className="update-dialog-body">
          <PropertyRow label="当前版本" value={applicationVersion} />
          {availableVersion ? <PropertyRow label="可用版本" value={availableVersion} /> : null}
          <div className="update-message" data-status={status}>{message}</div>
        </div>
        <footer className="update-dialog-actions">
          <button className="secondary-button" type="button" onClick={onClose}>关闭</button>
          {status === "available" ? (
            <button className="primary-button" type="button" onClick={() => void installUpdate()}>
              <Download aria-hidden="true" size={15} />
              下载并安装
            </button>
          ) : (
            <button
              className="primary-button"
              disabled={status === "checking" || status === "installing"}
              type="button"
              onClick={() => void checkForUpdate()}
            >
              检查更新
            </button>
          )}
        </footer>
      </section>
    </div>
  );
}

type ContextSidebarProps = {
  activeRail: string;
  jobs: Job[];
  project: Project;
  assets: Asset[];
  fileTree: ProjectFileNode[];
  showHidden: boolean;
  importing: boolean;
  projectReady: boolean;
  selectedJobId: string | null;
  selectedFilePath: string | null;
  selectedAnalysis: string;
  onImport: () => void;
  onSelectAnalysis: (analysis: string) => void;
  onSelectFile: (file: ProjectFileNode) => void;
  onSelectJob: (jobId: string) => void;
  onShowHiddenChange: (value: boolean) => void;
};

function ContextSidebar({
  activeRail,
  jobs,
  project,
  assets,
  fileTree,
  showHidden,
  importing,
  projectReady,
  selectedJobId,
  selectedFilePath,
  selectedAnalysis,
  onImport,
  onSelectAnalysis,
  onSelectFile,
  onSelectJob,
  onShowHiddenChange,
}: ContextSidebarProps) {
  const [searchText, setSearchText] = useState("");
  const [expandedPaths, setExpandedPaths] = useState<Set<string>>(
    () => new Set(["", "source", "documents", "datasets"]),
  );
  const normalizedSearch = searchText.trim().toLocaleLowerCase("zh-CN");
  const visibleTree = normalizedSearch ? filterProjectTree(fileTree, normalizedSearch) : fileTree;

  function toggleDirectory(relativePath: string) {
    setExpandedPaths((current) => {
      const next = new Set(current);
      if (next.has(relativePath)) {
        next.delete(relativePath);
      } else {
        next.add(relativePath);
      }
      return next;
    });
  }

  return (
    <aside className="context-sidebar">
      <div className="sidebar-header">
        <div>
          <span className="section-kicker">当前工作区</span>
          <button className="project-switcher" type="button">
            <span>{project.name}</span>
            <ChevronDown aria-hidden="true" size={15} />
          </button>
        </div>
        <button
          className="icon-button"
          title={importing ? "正在导入" : "导入文件"}
          type="button"
          disabled={importing || !projectReady}
          onClick={onImport}
        >
          <Import aria-hidden="true" size={17} />
          <span className="sr-only">导入文件</span>
        </button>
      </div>

      <label className="search-box">
        <Search aria-hidden="true" size={15} />
        <input
          aria-label="搜索项目内容"
          placeholder="搜索项目内容"
          value={searchText}
          onChange={(event) => setSearchText(event.target.value)}
        />
      </label>

      {activeRail === "models" ? (
        <section className="sidebar-section sidebar-fill-section">
          <SectionTitle icon={Box} title="分析方法" />
          <div className="analysis-nav-list">
            {analysisMethods.map((method) => {
              const Icon = method.icon;
              return (
                <button
                  key={method.id}
                  className="analysis-nav-row"
                  data-active={selectedAnalysis === method.id}
                  type="button"
                  onClick={() => onSelectAnalysis(method.id)}
                >
                  <Icon aria-hidden="true" size={16} />
                  <span><strong>{method.label}</strong><small>{method.group}</small></span>
                </button>
              );
            })}
          </div>
        </section>
      ) : activeRail === "tools" ? (
        <section className="sidebar-section sidebar-fill-section">
          <SectionTitle icon={Wrench} title="可用工具" />
          <div className="analysis-nav-list">
            <SidebarAction icon={Import} label="导入和解压" detail="文件与压缩包" onClick={onImport} />
            <SidebarAction icon={FileText} label="文档解析" detail="PDF 和 OCR" onClick={() => undefined} />
            <SidebarAction icon={Database} label="数据集导出" detail="Parquet" onClick={() => undefined} />
          </div>
        </section>
      ) : (
      <section className="sidebar-section sidebar-fill-section">
        <SectionTitle
          icon={ListTree}
          title="项目内容"
          action={(
            <button
              className="section-icon-action"
              data-active={showHidden}
              title={showHidden ? "隐藏隐藏项目" : "显示隐藏项目"}
              type="button"
              onClick={() => onShowHiddenChange(!showHidden)}
            >
              {showHidden ? <Eye aria-hidden="true" size={14} /> : <EyeOff aria-hidden="true" size={14} />}
              <span className="sr-only">{showHidden ? "隐藏隐藏项目" : "显示隐藏项目"}</span>
            </button>
          )}
        />
        <div className="asset-tree">
          <TreeRow
            icon={expandedPaths.has("") ? FolderOpen : Folder}
            label={project.name}
            level={0}
            open={expandedPaths.has("")}
            onClick={() => toggleDirectory("")}
          />
          {expandedPaths.has("") && visibleTree.length > 0 ? (
            visibleTree.map((node) => (
              <ProjectTreeNode
                key={node.relativePath}
                node={node}
                level={1}
                expandedPaths={expandedPaths}
                forceOpen={Boolean(normalizedSearch)}
                selectedFilePath={selectedFilePath}
                onSelectFile={onSelectFile}
                onToggle={toggleDirectory}
              />
            ))
          ) : (
            <div className="tree-empty">项目目录为空</div>
          )}
        </div>
      </section>
      )}

      {activeRail === "workspace" || activeRail === "jobs" ? <section className="sidebar-section history-section">
        <SectionTitle icon={History} title="任务历史" actionLabel="查看全部" />
        <div className="job-list">
          {jobs.map((job) => (
            <button
              key={job.id}
              className="job-row"
              data-active={selectedJobId === job.id}
              type="button"
              onClick={() => onSelectJob(job.id)}
            >
              <span className={`status-dot status-${job.status}`} />
              <span className="job-row-copy">
                <strong>{job.title}</strong>
                <span>{statusLabels[job.status]}</span>
              </span>
              <span className="job-time">{formatTime(job.updatedAt)}</span>
            </button>
          ))}
        </div>
      </section> : null}

      <div className="sidebar-footer">
        <span>本地项目</span>
        <span>{assets.length} 个资产</span>
      </div>
    </aside>
  );
}

type SectionTitleProps = {
  icon: typeof History;
  title: string;
  actionLabel?: string;
  action?: ReactNode;
};

function SectionTitle({ icon: Icon, title, actionLabel, action }: SectionTitleProps) {
  return (
    <div className="section-title">
      <span>
        <Icon aria-hidden="true" size={14} />
        {title}
      </span>
      {action ?? (actionLabel ? (
        <button type="button">{actionLabel}</button>
      ) : null)}
    </div>
  );
}

type TreeRowProps = {
  icon: typeof Folder;
  label: string;
  level: number;
  open?: boolean;
  active?: boolean;
  hidden?: boolean;
  onClick?: () => void;
};

function TreeRow({ icon: Icon, label, level, open = false, active = false, hidden = false, onClick }: TreeRowProps) {
  return (
    <button
      className="tree-row"
      data-active={active}
      data-hidden={hidden}
      style={{ paddingLeft: `${10 + level * 16}px` }}
      title={label}
      type="button"
      onClick={onClick}
    >
      {Icon === Folder || Icon === FolderOpen ? (
        open ? (
          <ChevronDown aria-hidden="true" size={13} />
        ) : (
          <ChevronRight aria-hidden="true" size={13} />
        )
      ) : (
        <span className="tree-spacer" />
      )}
      <Icon aria-hidden="true" size={15} strokeWidth={1.8} />
      <span>{label}</span>
    </button>
  );
}

function ProjectTreeNode({
  node,
  level,
  expandedPaths,
  forceOpen,
  selectedFilePath,
  onSelectFile,
  onToggle,
}: {
  node: ProjectFileNode;
  level: number;
  expandedPaths: Set<string>;
  forceOpen: boolean;
  selectedFilePath: string | null;
  onSelectFile: (file: ProjectFileNode) => void;
  onToggle: (path: string) => void;
}) {
  const directoryOpen = forceOpen || expandedPaths.has(node.relativePath);
  const icon = node.kind === "directory"
    ? directoryOpen ? FolderOpen : Folder
    : fileIconForName(node.name);
  return (
    <>
      <TreeRow
        icon={icon}
        label={node.name}
        level={level}
        open={directoryOpen}
        active={node.relativePath === selectedFilePath}
        hidden={node.hidden}
        onClick={() => {
          if (node.kind === "directory") {
            onToggle(node.relativePath);
          } else {
            onSelectFile(node);
          }
        }}
      />
      {node.kind === "directory" && directoryOpen
        ? node.children.map((child) => (
            <ProjectTreeNode
              key={child.relativePath}
              node={child}
              level={level + 1}
              expandedPaths={expandedPaths}
              forceOpen={forceOpen}
              selectedFilePath={selectedFilePath}
              onSelectFile={onSelectFile}
              onToggle={onToggle}
            />
          ))
        : null}
    </>
  );
}

function SidebarAction({ icon: Icon, label, detail, onClick }: { icon: typeof Import; label: string; detail: string; onClick: () => void }) {
  return (
    <button className="analysis-nav-row" type="button" onClick={onClick}>
      <Icon aria-hidden="true" size={16} />
      <span><strong>{label}</strong><small>{detail}</small></span>
    </button>
  );
}

type WorkspaceHeaderProps = {
  activeRail: string;
  health: ServiceHealth | null;
  preview: TablePreview | null;
  project: Project;
  serviceError: string | null;
  selectedAsset: Asset | null;
  selectedFile: ProjectFileNode | null;
  inspectorVisible: boolean;
  onToggleInspector: () => void;
};

function WorkspaceHeader({
  activeRail,
  health,
  preview,
  project,
  serviceError,
  selectedAsset,
  selectedFile,
  inspectorVisible,
  onToggleInspector,
}: WorkspaceHeaderProps) {
  const activeLabel =
    railItems.find((item) => item.id === activeRail)?.label ?? "工作台";

  return (
    <header className="workspace-header">
      <div className="workspace-title">
        <span className="breadcrumb">{project.name} / {activeLabel}</span>
        <h1>{selectedFile?.name ?? selectedAsset?.name ?? preview?.sourceName ?? activeLabel}</h1>
      </div>

      <div className="header-actions">
        <div
          className="service-status"
          data-connected={Boolean(health)}
          title={serviceError ?? health?.service ?? "正在连接本地任务服务"}
        >
          <span />
          {health ? "本地服务已连接" : "本地服务未连接"}
        </div>
        <button
          className="icon-button"
          title={inspectorVisible ? "收起检查栏" : "展开检查栏"}
          type="button"
          onClick={onToggleInspector}
        >
          <PanelRightClose aria-hidden="true" size={17} />
          <span className="sr-only">{inspectorVisible ? "收起检查栏" : "展开检查栏"}</span>
        </button>
      </div>
    </header>
  );
}

function WorkflowBar({ activeRail, job, preview }: { activeRail: string; job: Job | null; preview: TablePreview | null }) {
  const steps = activeRail === "documents"
    ? ["读取文件", "页面解析", "内容检查", "格式导出"]
    : ["导入", "字段检查", "训练配置", "模型训练", "结果评估"];
  const documentIndex = activeRail === "documents" ? 2 : null;
  const activeIndex = preview ? 1 : job?.status === "succeeded" ? 4 : job ? 3 : 0;

  return (
    <div
      className="workflow-bar"
      aria-label="当前工作流"
      style={{ gridTemplateColumns: `repeat(${steps.length}, minmax(96px, 1fr))` }}
    >
      {steps.map((step, index) => (
        <div
          key={step}
          className="workflow-step"
          data-state={
            index < (documentIndex ?? activeIndex)
              ? "complete"
              : index === (documentIndex ?? activeIndex)
                ? "active"
                : "pending"
          }
        >
          <span className="step-index">{index + 1}</span>
          <span>{step}</span>
        </div>
      ))}
    </div>
  );
}

type WorkspaceContentProps = {
  activeRail: string;
  job: Job | null;
  jobs: Job[];
  project: Project;
  preview: TablePreview | null;
  importError: WorkspaceError | null;
  importing: boolean;
  confirming: boolean;
  dataset: DatasetVersion | null;
  documentResult: DocumentParseResult | null;
  selectedAsset: Asset | null;
  selectedFile: ProjectFileNode | null;
  selectedAnalysis: string;
  modelPlanStatus: string;
  trainingResult: TrainingResult | null;
  projectReady: boolean;
  onImport: () => void;
  onConfirm: () => void;
  onExport: () => void;
  onSelectAnalysis: (analysis: string) => void;
  onCreateModelPlan: (payload: TrainingCreate) => void;
};

function WorkspaceContent({
  activeRail,
  job,
  jobs,
  project,
  preview,
  importError,
  importing,
  confirming,
  dataset,
  documentResult,
  selectedAsset,
  selectedFile,
  selectedAnalysis,
  modelPlanStatus,
  trainingResult,
  projectReady,
  onImport,
  onConfirm,
  onExport,
  onSelectAnalysis,
  onCreateModelPlan,
}: WorkspaceContentProps) {
  const numericColumnCount =
    preview?.columns.filter((column) =>
      ["integer", "number"].includes(column.inferredType),
    ).length ?? 0;

  if (activeRail === "documents") {
    return (
      <DocumentWorkspace
        asset={selectedAsset}
        document={documentResult}
        file={selectedFile}
        projectId={project.id}
        onImport={onImport}
      />
    );
  }

  if (activeRail === "models") {
    return (
      <ModelWorkspace
        dataset={dataset}
        selectedAnalysis={selectedAnalysis}
        planStatus={modelPlanStatus}
        selectedJob={job}
        trainingResult={trainingResult}
        onSelectAnalysis={onSelectAnalysis}
        onCreatePlan={onCreateModelPlan}
      />
    );
  }

  if (activeRail === "jobs") {
    return <JobsWorkspace jobs={jobs} selectedJob={job} />;
  }

  if (activeRail === "tools") {
    return <ToolsWorkspace onImport={onImport} />;
  }

  if (!preview && !documentResult) {
    return (
      <div className="workspace-scroll empty-workspace">
        <Database aria-hidden="true" size={32} />
        <h2>从真实文件开始</h2>
        <p>导入表格后确认字段类型并创建数据集版本，导入 PDF 后可在文档工作区查看原件、解析内容和导出结果。</p>
        <button className="primary-button" type="button" onClick={onImport} disabled={importing || !projectReady}>
          <Import aria-hidden="true" size={15} />
          {importing ? "正在导入" : "导入文件"}
        </button>
      </div>
    );
  }

  return (
    <div className="workspace-scroll">
      <section className="summary-band">
        <div>
          <span className={`status-dot status-${preview ? "waiting_confirmation" : job?.status ?? "queued"}`} />
          <div>
            <span className="section-kicker">当前任务</span>
            <h2>{preview ? `检查 ${preview.sourceName} 的字段` : job?.title ?? "等待训练任务"}</h2>
            <p>{preview ? `已读取 ${preview.rowCount.toLocaleString("zh-CN")} 行数据，请确认字段类型和空值。` : job?.message ?? "请先选择数据集并在模型工作区创建训练任务。"}</p>
          </div>
        </div>
        <div className="task-controls">
          {!preview ? (
            <button className="secondary-button" type="button">
              <CircleStop aria-hidden="true" size={15} />
              停止
            </button>
          ) : null}
          <button className="primary-button" type="button" onClick={onConfirm} disabled={!preview || confirming}>
            <Play aria-hidden="true" size={15} />
            {preview ? confirming ? "正在创建" : dataset ? `数据集 v${dataset.version}` : "确认字段" : "继续运行"}
          </button>
        </div>
      </section>

      {importError ? (
        <section className="import-error" role="alert">
          <strong>{importError.errorType}</strong>
          <span>{importError.message}</span>
          <code>{importError.operation}</code>
        </section>
      ) : null}

      <section className="metrics-strip" aria-label="数据集摘要">
        <Metric
          label="数据行"
          value={documentResult ? String(documentResult.pageCount) : preview ? preview.rowCount.toLocaleString("zh-CN") : "48,216"}
          detail={documentResult ? "PDF 页数" : preview ? `预览前 ${preview.rows.length} 行` : "已过滤 126 行"}
        />
        <Metric
          label="字段"
          value={documentResult ? documentResult.pdfType : preview ? String(preview.columnCount) : "24"}
          detail={documentResult ? `OCR 已处理 ${documentResult.ocrPages.length} 页` : preview ? `数值 ${numericColumnCount}, 其他 ${preview.columnCount - numericColumnCount}` : "数值 15, 类别 9"}
        />
        <Metric
          label="文件格式"
          value={documentResult ? "PDF" : preview?.format.toUpperCase() ?? "XLSX"}
          detail={documentResult?.engine ?? preview?.sheetName ?? preview?.encoding ?? "销售数据集 v3"}
        />
        <Metric
          label="当前状态"
          value={documentResult ? documentResult.status : preview ? "待检查" : "训练中"}
          detail={documentResult ? (documentResult.status === "ocr_required" ? "等待 OCR Worker" : "文档已解析") : preview ? "请确认字段类型" : "验证 R2 0.872"}
        />
      </section>

      {documentResult ? (
        <section className="content-section document-preview-section">
          <div className="content-heading"><div><span className="section-kicker">文档预览</span><h2>{documentResult.pdfType}</h2></div></div>
          {documentResult.markdownPreview ? <pre>{documentResult.markdownPreview}</pre> : (
            <div className="document-ocr-state"><strong>需要 OCR</strong><span>待处理页: {documentResult.pagesNeedingOcr.join(", ")}</span></div>
          )}
        </section>
      ) : <section className="content-section">
        <div className="content-heading">
          <div>
            <span className="section-kicker">数据预览</span>
            <h2>{preview?.sourceName ?? "销售数据集 v3"}</h2>
          </div>
          <div className="content-actions">
            <button className="icon-button" title="筛选字段" type="button">
              <SlidersHorizontal aria-hidden="true" size={16} />
              <span className="sr-only">筛选字段</span>
            </button>
            <button className="secondary-button" type="button" onClick={onImport} disabled={importing || !projectReady}>
              <Import aria-hidden="true" size={15} />
              {importing ? "正在导入" : projectReady ? "导入数据" : "正在打开项目"}
            </button>
            {dataset ? (
              <button className="secondary-button" type="button" onClick={onExport}>
                <Archive aria-hidden="true" size={15} />
                导出 Parquet
              </button>
            ) : null}
          </div>
        </div>

        <div className="data-table-shell">
          <table>
            <thead>
              {preview ? (
                <tr>
                  {preview.columns.map((column) => (
                    <th
                      key={column.name}
                      className={isNumericType(column.inferredType) ? "number-cell" : undefined}
                      title={`${column.name}, ${column.inferredType}`}
                    >
                      {column.name}
                    </th>
                  ))}
                </tr>
              ) : (
                <tr>
                  <th>日期</th><th>区域</th><th>产品类别</th><th>渠道</th>
                  <th className="number-cell">销量</th><th className="number-cell">销售额</th>
                </tr>
              )}
            </thead>
            <tbody>
              {preview ? preview.rows.map((row, rowIndex) => (
                <tr key={rowIndex}>
                  {preview.columns.map((column) => (
                    <td
                      key={column.name}
                      className={isNumericType(column.inferredType) ? "number-cell" : undefined}
                      title={formatCell(row[column.name])}
                    >
                      {formatCell(row[column.name])}
                    </td>
                  ))}
                </tr>
              )) : <DemoTableRows />}
            </tbody>
          </table>
        </div>
        <div className="table-footer">
          <span>{preview ? `显示前 ${preview.rows.length} 行, 共 ${preview.rowCount.toLocaleString("zh-CN")} 行` : "显示前 4 行, 共 48,216 行"}</span>
          <span>来源: {preview?.sourceName ?? project.path}</span>
        </div>
      </section>}

      <section className="content-section activity-section">
        <div className="content-heading">
          <div>
            <span className="section-kicker">执行记录</span>
            <h2>{preview ? "导入活动" : "训练活动"}</h2>
          </div>
          <button className="text-button" type="button">
            查看完整日志
          </button>
        </div>
        <div className="activity-list">
          {preview ? (
            <>
              <ActivityRow time="刚刚" title="原始文件已保存" detail={`${preview.sourceName}, SHA-256 已记录`} state="complete" />
              <ActivityRow time="刚刚" title="表格结构已读取" detail={`${preview.columnCount} 个字段, ${preview.rowCount.toLocaleString("zh-CN")} 行`} state="complete" />
              <ActivityRow time="当前" title="等待字段确认" detail="确认字段类型后可创建数据集版本" state="active" />
            </>
          ) : job ? (
            <ActivityRow time={formatTime(job.updatedAt)} title={job.title} detail={job.message ?? statusLabels[job.status]} state={job.status === "running" ? "active" : "complete"} />
          ) : <ActivityRow time="当前" title="暂无执行记录" detail="创建训练任务后显示真实 Worker 状态" state="active" />}
        </div>
      </section>
    </div>
  );
}

function DocumentWorkspace({
  asset,
  document,
  file,
  projectId,
  onImport,
}: {
  asset: Asset | null;
  document: DocumentParseResult | null;
  file: ProjectFileNode | null;
  projectId: string;
  onImport: () => void;
}) {
  const [viewMode, setViewMode] = useState<"original" | "parsed">("original");
  const [exportFormat, setExportFormat] = useState<"docx" | "xlsx" | "md" | "txt">("docx");

  if (!file && (!asset || !document)) {
    return (
      <div className="workspace-scroll empty-workspace">
        <FileText aria-hidden="true" size={32} />
        <h2>选择一个项目文件</h2>
        <p>从左侧项目树选择文件，或者先导入一个 PDF 文档。</p>
        <button className="primary-button" type="button" onClick={onImport}>
          <Import aria-hidden="true" size={15} />
          导入文档
        </button>
      </div>
    );
  }

  const fileName = file?.name ?? asset?.name ?? "项目文件";
  const contentUrl = asset
    ? workspaceClient.getAssetContentUrl(asset.id)
    : workspaceClient.getProjectFileContentUrl(projectId, file!.relativePath);
  const exportUrl = asset && document
    ? workspaceClient.getDocumentExportUrl(asset.id, exportFormat)
    : null;
  return (
    <div className="document-workspace">
      <div className="document-toolbar">
        <div className="view-segmented" role="tablist" aria-label="文档视图">
          <button data-active={viewMode === "original"} type="button" onClick={() => setViewMode("original")}>原文件</button>
          <button disabled={!document} data-active={viewMode === "parsed"} type="button" onClick={() => setViewMode("parsed")}>解析内容</button>
        </div>
        {exportUrl ? <div className="document-export-controls">
          <label>
            <span className="sr-only">导出格式</span>
            <select value={exportFormat} onChange={(event) => setExportFormat(event.target.value as typeof exportFormat)}>
              <option value="docx">Word DOCX</option>
              <option value="xlsx">Excel XLSX</option>
              <option value="md">Markdown</option>
              <option value="txt">纯文本 TXT</option>
            </select>
          </label>
          <a className="secondary-button button-link" href={exportUrl} download>
            <FileDown aria-hidden="true" size={15} />
            导出解析结果
          </a>
        </div> : <span className="document-file-note">项目文件只读预览</span>}
      </div>

      {viewMode === "original" ? (
        fileName.toLowerCase().endsWith(".pdf") ? (
          <PdfDocumentViewer fileName={fileName} url={contentUrl} />
        ) : isTextPreviewFile(fileName) ? (
          <TextFileViewer fileName={fileName} url={contentUrl} />
        ) : (
          <iframe className="office-document-frame" src={contentUrl} title={`${fileName} 原文件预览`} />
        )
      ) : document ? (
        <div className="parsed-document-pages">
          <header className="parsed-document-header">
            <div><span className="section-kicker">完整解析内容</span><h2>{fileName}</h2></div>
            <span>{document.pageCount} 页</span>
          </header>
          {document.pages.map((page) => (
            <article className="parsed-document-page" key={page.pageNumber}>
              <header>第 {page.pageNumber} 页</header>
              <div>{page.text || "本页没有识别到文本"}</div>
            </article>
          ))}
        </div>
      ) : null}
    </div>
  );
}

function TextFileViewer({ fileName, url }: { fileName: string; url: string }) {
  const [content, setContent] = useState<string | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    setContent(null);
    setLoadError(null);
    void fetch(url, { signal: controller.signal })
      .then((response) => response.ok ? response.text() : Promise.reject(new Error(`HTTP ${response.status}`)))
      .then(setContent)
      .catch((error: unknown) => {
        if (!(error instanceof DOMException && error.name === "AbortError")) {
          setLoadError(error instanceof Error ? error.message : "文本文件读取失败");
        }
      });
    return () => controller.abort();
  }, [url]);

  if (loadError) {
    return <div className="text-file-state"><FileText aria-hidden="true" size={28} /><strong>无法读取项目文本</strong><span>{loadError}</span></div>;
  }
  if (content === null) {
    return <div className="text-file-state"><FileText aria-hidden="true" size={28} /><strong>正在读取文件</strong><span>{fileName}</span></div>;
  }
  return (
    <article className="text-file-viewer">
      <header><strong>{fileName}</strong><span>{fileName.toLowerCase().endsWith(".json") ? "JSON" : "文本"}</span></header>
      <pre>{formatTextPreview(fileName, content)}</pre>
    </article>
  );
}

type PdfDocumentProxy = import("pdfjs-dist").PDFDocumentProxy;

function PdfDocumentViewer({ fileName, url }: { fileName: string; url: string }) {
  const [pdf, setPdf] = useState<PdfDocumentProxy | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    let disposed = false;
    let loadingTask: ReturnType<typeof import("pdfjs-dist")["getDocument"]> | null = null;

    void Promise.all([
      import("pdfjs-dist"),
      import("pdfjs-dist/build/pdf.worker.min.mjs?url"),
    ]).then(([pdfjs, workerModule]) => {
      if (disposed) {
        return;
      }
      pdfjs.GlobalWorkerOptions.workerSrc = workerModule.default;
      const pdfAssetRoot = new URL("./pdfjs/", document.baseURI);
      loadingTask = pdfjs.getDocument({
        url,
        cMapUrl: new URL("cmaps/", pdfAssetRoot).toString(),
        cMapPacked: true,
        iccUrl: new URL("iccs/", pdfAssetRoot).toString(),
        standardFontDataUrl: new URL("standard_fonts/", pdfAssetRoot).toString(),
        wasmUrl: new URL("wasm/", pdfAssetRoot).toString(),
      });
      return loadingTask.promise;
    }).then((loadedPdf) => {
      if (loadedPdf && !disposed) {
        setPdf(loadedPdf);
        setLoadError(null);
      }
    }).catch((error: unknown) => {
      if (!disposed) {
        setLoadError(error instanceof Error ? error.message : "PDF 原文件加载失败");
      }
    });

    return () => {
      disposed = true;
      void loadingTask?.destroy();
    };
  }, [url]);

  if (loadError) {
    return <div className="pdf-viewer-state"><FileText aria-hidden="true" size={28} /><strong>无法显示 PDF 原文件</strong><span>{loadError}</span></div>;
  }
  if (!pdf) {
    return <div className="pdf-viewer-state"><FileText aria-hidden="true" size={28} /><strong>正在读取 PDF</strong><span>{fileName}</span></div>;
  }

  return (
    <div className="pdf-original-pages" aria-label={`${fileName} 原文件完整预览`}>
      <header><strong>{fileName}</strong><span>{pdf.numPages} 页</span></header>
      {Array.from({ length: pdf.numPages }, (_, index) => (
        <PdfCanvasPage key={index + 1} pageNumber={index + 1} pdf={pdf} />
      ))}
    </div>
  );
}

function PdfCanvasPage({ pageNumber, pdf }: { pageNumber: number; pdf: PdfDocumentProxy }) {
  const containerRef = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [renderError, setRenderError] = useState<string | null>(null);

  useEffect(() => {
    const container = containerRef.current;
    const canvas = canvasRef.current;
    if (!container || !canvas) {
      return;
    }
    const pageContainer = container;
    const pageCanvas = canvas;
    let disposed = false;
    let renderTask: { cancel: () => void; promise: Promise<unknown> } | null = null;

    async function renderPage() {
      renderTask?.cancel();
      const page = await pdf.getPage(pageNumber);
      if (disposed) {
        return;
      }
      const baseViewport = page.getViewport({ scale: 1 });
      const availableWidth = Math.max(pageContainer.clientWidth - 32, 240);
      const scale = Math.min(availableWidth / baseViewport.width, 1.8);
      const viewport = page.getViewport({ scale });
      const pixelRatio = Math.min(window.devicePixelRatio || 1, 2);
      if (!pageCanvas.getContext("2d")) {
        throw new Error("浏览器无法创建 PDF 画布上下文");
      }
      pageCanvas.width = Math.floor(viewport.width * pixelRatio);
      pageCanvas.height = Math.floor(viewport.height * pixelRatio);
      pageCanvas.style.width = `${Math.floor(viewport.width)}px`;
      pageCanvas.style.height = `${Math.floor(viewport.height)}px`;
      renderTask = page.render({
        canvas: pageCanvas,
        viewport,
        transform: pixelRatio === 1 ? undefined : [pixelRatio, 0, 0, pixelRatio, 0, 0],
      });
      await renderTask.promise;
      if (!disposed) {
        setRenderError(null);
      }
    }

    let resizeTimer: number | null = null;
    let observedWidth = 0;
    const observer = new ResizeObserver((entries) => {
      const nextWidth = entries[0]?.contentRect.width ?? pageContainer.clientWidth;
      if (Math.abs(nextWidth - observedWidth) < 1) {
        return;
      }
      observedWidth = nextWidth;
      if (resizeTimer !== null) {
        window.clearTimeout(resizeTimer);
      }
      resizeTimer = window.setTimeout(() => void renderPage().catch((error: unknown) => {
        if (!disposed && !(error instanceof Error && error.name === "RenderingCancelledException")) {
          setRenderError(error instanceof Error ? error.message : "PDF 页面渲染失败");
        }
      }), 80);
    });
    observer.observe(pageContainer);

    return () => {
      disposed = true;
      observer.disconnect();
      if (resizeTimer !== null) {
        window.clearTimeout(resizeTimer);
      }
      renderTask?.cancel();
    };
  }, [pageNumber, pdf]);

  return (
    <article className="pdf-original-page" ref={containerRef}>
      <header>第 {pageNumber} 页</header>
      {renderError ? <div className="pdf-page-error">{renderError}</div> : null}
      <canvas ref={canvasRef} />
    </article>
  );
}

function ModelWorkspace({
  dataset,
  selectedAnalysis,
  planStatus,
  selectedJob,
  trainingResult,
  onSelectAnalysis,
  onCreatePlan,
}: {
  dataset: DatasetVersion | null;
  selectedAnalysis: string;
  planStatus: string;
  selectedJob: Job | null;
  trainingResult: TrainingResult | null;
  onSelectAnalysis: (analysis: string) => void;
  onCreatePlan: (payload: TrainingCreate) => void;
}) {
  const [targetColumn, setTargetColumn] = useState("");
  const [validationRatio, setValidationRatio] = useState(20);
  const [randomSeed, setRandomSeed] = useState(42);
  const [computeMode, setComputeMode] = useState("auto");
  const [activeView, setActiveView] = useState("design");
  const method = analysisMethods.find((item) => item.id === selectedAnalysis) ?? analysisMethods[0]!;
  const targetRequired = selectedAnalysis !== "clustering";

  useEffect(() => {
    if (!dataset) {
      setTargetColumn("");
      return;
    }
    const defaultTarget = dataset.columns.find((column) => ["integer", "number"].includes(column.dataType))?.name ?? dataset.columns[0]?.name ?? "";
    setTargetColumn((current) => dataset.columns.some((column) => column.name === current) ? current : defaultTarget);
  }, [dataset]);

  return (
    <div className="workspace-scroll model-workspace">
      <div className="model-view-tabs" role="tablist" aria-label="模型工作区视图">
        {[
          { id: "design", label: "任务设计" },
          { id: "monitor", label: "训练监控" },
          { id: "evaluation", label: "评估结果" },
        ].map((view) => (
          <button key={view.id} data-active={activeView === view.id} type="button" onClick={() => setActiveView(view.id)}>{view.label}</button>
        ))}
      </div>

      {activeView === "design" ? (
        <>
          <section className="model-intro-band">
            <div><span className="section-kicker">分析任务</span><h2>{method.label}</h2><p>{method.detail}。先选择方法，再确认数据、字段和验证方式。</p></div>
            <div><span>可用数据集</span><strong>{dataset ? 1 : 0}</strong></div>
          </section>

          <section className="analysis-method-section">
            <div className="section-heading"><div><span className="section-kicker">方法选择</span><h2>选择分析目标</h2></div></div>
            <div className="analysis-method-grid">
              {analysisMethods.map((item) => {
                const Icon = item.icon;
                return (
                  <button key={item.id} data-active={selectedAnalysis === item.id} type="button" onClick={() => onSelectAnalysis(item.id)}>
                    <Icon aria-hidden="true" size={19} />
                    <span><strong>{item.label}</strong><small>{item.group}</small><p>{item.detail}</p></span>
                  </button>
                );
              })}
            </div>
          </section>

          <section className="model-config-section">
            <div className="section-heading"><div><span className="section-kicker">任务参数</span><h2>数据和运行配置</h2></div></div>
            <div className="model-config-grid">
              <div className="config-column">
                <label><span>数据集</span><select value={dataset?.id ?? ""} disabled><option value="">请先创建数据集版本</option>{dataset ? <option value={dataset.id}>数据集 v{dataset.version}</option> : null}</select></label>
                <label><span>{targetRequired ? "目标字段" : "分组字段"}</span><select value={targetColumn} disabled={!dataset || !targetRequired} onChange={(event) => setTargetColumn(event.target.value)}><option value="">请选择字段</option>{dataset?.columns.map((column) => <option key={column.name} value={column.name}>{column.name}</option>)}</select></label>
                <label><span>验证集比例</span><div className="range-control"><input type="range" min="10" max="40" step="5" value={validationRatio} onChange={(event) => setValidationRatio(Number(event.target.value))} /><output>{validationRatio}%</output></div></label>
                <label><span>随机种子</span><input type="number" value={randomSeed} onChange={(event) => setRandomSeed(Number(event.target.value))} /></label>
              </div>
              <div className="config-column">
                <span className="config-label">计算模式</span>
                <div className="compute-segmented">
                  {[{ id: "auto", label: "自动" }, { id: "cpu", label: "CPU" }, { id: "gpu", label: "GPU" }].map((mode) => (
                    <button key={mode.id} data-active={computeMode === mode.id} type="button" onClick={() => setComputeMode(mode.id)}>{mode.label}</button>
                  ))}
                </div>
                <div className="plan-summary">
                  <PropertyRow label="分析方法" value={method.label} />
                  <PropertyRow label={targetRequired ? "目标字段" : "无监督任务"} value={targetRequired ? targetColumn || "未选择" : "不需要目标字段"} />
                  <PropertyRow label="验证比例" value={`${validationRatio}%`} />
                  <PropertyRow label="计算位置" value={computeMode.toUpperCase()} />
                  <PropertyRow label="随机种子" value={String(randomSeed)} />
                </div>
              </div>
            </div>
            <div className="model-plan-footer">
              <span>{planStatus}</span>
              <button className="primary-button" disabled={!dataset || (targetRequired && !targetColumn)} type="button" onClick={() => {
                if (!dataset) {
                  return;
                }
                onCreatePlan({ datasetId: dataset.id, method: selectedAnalysis as TrainingCreate["method"], targetColumn: targetRequired ? targetColumn : null, validationRatio, randomSeed, computeMode: computeMode as TrainingCreate["computeMode"] });
                setActiveView("monitor");
              }}><Play aria-hidden="true" size={15} />启动本地训练</button>
            </div>
          </section>
        </>
      ) : activeView === "monitor" ? (
        <section className="workspace-state-view"><BarChart3 aria-hidden="true" size={30} /><h2>{selectedJob ? selectedJob.title : "训练监控"}</h2><p>{selectedJob ? `${statusLabels[selectedJob.status]}，进度 ${selectedJob.progress}%。${selectedJob.message ?? ""}` : "创建数据集并启动训练后，这里显示 Worker 的真实状态。"}</p></section>
      ) : (
        <section className="workspace-state-view"><LineChart aria-hidden="true" size={30} /><h2>评估结果</h2>{trainingResult?.status === "succeeded" ? <div className="training-metrics">{Object.entries(trainingResult.metrics).map(([name, value]) => <span key={name}>{name}: {value.toFixed(4)}</span>)}</div> : <p>{trainingResult?.errorMessage ?? "任务完成后，这里显示真实指标和模型产物路径。"}</p>}</section>
      )}
    </div>
  );
}

function JobsWorkspace({ jobs, selectedJob }: { jobs: Job[]; selectedJob: Job | null }) {
  return (
    <div className="workspace-scroll module-workspace">
      <div className="section-heading"><div><span className="section-kicker">运行记录</span><h2>任务队列</h2></div><span>{jobs.length} 个任务</span></div>
      <div className="module-list">
        {jobs.map((item) => <ActivityRow key={item.id} time={formatTime(item.updatedAt)} title={item.title} detail={item.message ?? statusLabels[item.status]} state={item.id === selectedJob?.id ? "active" : "complete"} />)}
      </div>
    </div>
  );
}

function ToolsWorkspace({ onImport }: { onImport: () => void }) {
  return (
    <div className="workspace-scroll module-workspace">
      <div className="section-heading"><div><span className="section-kicker">本地能力</span><h2>工具目录</h2></div></div>
      <div className="tool-grid">
        <button type="button" onClick={onImport}><Import aria-hidden="true" size={20} /><span><strong>导入文件</strong><small>CSV、XLSX、PDF 和压缩包</small></span></button>
        <button type="button"><FileText aria-hidden="true" size={20} /><span><strong>文档解析</strong><small>文本层、OCR 和结构化输出</small></span></button>
        <button type="button"><Database aria-hidden="true" size={20} /><span><strong>数据集版本</strong><small>字段确认和 Parquet 导出</small></span></button>
        <button type="button"><Box aria-hidden="true" size={20} /><span><strong>模型分析</strong><small>统计、机器学习和深度学习</small></span></button>
      </div>
    </div>
  );
}

function Metric({
  label,
  value,
  detail,
}: {
  label: string;
  value: string;
  detail: string;
}) {
  return (
    <div className="metric-item">
      <span>{label}</span>
      <strong>{value}</strong>
      <small>{detail}</small>
    </div>
  );
}

function DemoTableRows() {
  return (
    <>
      <tr>
        <td>2026-07-01</td><td>上海</td><td>办公设备</td><td>直营网点</td>
        <td className="number-cell">318</td><td className="number-cell">286,420.00</td>
      </tr>
      <tr>
        <td>2026-07-01</td><td>江苏</td><td>耗材</td><td>电商</td>
        <td className="number-cell">1,284</td><td className="number-cell">174,036.50</td>
      </tr>
      <tr>
        <td>2026-07-02</td><td>浙江</td><td>家具</td><td>经销商</td>
        <td className="number-cell">96</td><td className="number-cell">321,680.00</td>
      </tr>
      <tr>
        <td>2026-07-02</td><td>安徽</td><td>办公设备</td><td>电商</td>
        <td className="number-cell">224</td><td className="number-cell">196,742.00</td>
      </tr>
    </>
  );
}

function isNumericType(type: string) {
  return type === "integer" || type === "number";
}

function formatCell(value: unknown) {
  if (value === null || value === undefined || value === "") {
    return "";
  }
  if (typeof value === "object") {
    return JSON.stringify(value);
  }
  return String(value);
}

function fileIconForName(name: string): typeof FileIcon {
  const suffix = name.toLowerCase().split(".").pop();
  if (["csv", "xls", "xlsx", "parquet"].includes(suffix ?? "")) {
    return FileSpreadsheet;
  }
  if (["pdf", "doc", "docx", "md", "txt"].includes(suffix ?? "")) {
    return FileText;
  }
  if (["zip", "tar", "tgz", "gz", "7z"].includes(suffix ?? "")) {
    return Archive;
  }
  return FileIcon;
}

export function filterProjectTree(nodes: ProjectFileNode[], searchText: string): ProjectFileNode[] {
  return nodes.flatMap((node) => {
    const children = filterProjectTree(node.children, searchText);
    if (node.name.toLocaleLowerCase("zh-CN").includes(searchText) || children.length > 0) {
      return [{ ...node, children }];
    }
    return [];
  });
}

function findProjectFile(nodes: ProjectFileNode[], relativePath: string): ProjectFileNode | null {
  for (const node of nodes) {
    if (node.relativePath === relativePath) {
      return node;
    }
    const nested = findProjectFile(node.children, relativePath);
    if (nested) {
      return nested;
    }
  }
  return null;
}

function isTextPreviewFile(fileName: string): boolean {
  return [".json", ".md", ".markdown", ".txt", ".yaml", ".yml"].some((suffix) => fileName.toLowerCase().endsWith(suffix));
}

function formatTextPreview(fileName: string, content: string): string {
  if (!fileName.toLowerCase().endsWith(".json")) {
    return content;
  }
  try {
    return JSON.stringify(JSON.parse(content), null, 2);
  } catch {
    return content;
  }
}

function asWorkspaceError(error: unknown, operation: string, fallbackMessage: string): WorkspaceError {
  if (error instanceof WorkspaceClientError) {
    return error.workspaceError;
  }
  return {
    errorType: error instanceof Error ? error.name : "LocalServiceError",
    message: error instanceof Error ? error.message : fallbackMessage,
    operation,
    recoverable: true,
    details: {},
  };
}

function formatBytes(size: number): string {
  if (size < 1024) {
    return `${size} B`;
  }
  if (size < 1024 * 1024) {
    return `${(size / 1024).toFixed(1)} KB`;
  }
  return `${(size / 1024 / 1024).toFixed(1)} MB`;
}

function createInitialFieldTypes(preview: TablePreview) {
  return Object.fromEntries(
    preview.columns.map((column) => [
      column.name,
      column.inferredType === "empty" ? "text" : column.inferredType,
    ]),
  ) as Record<string, DatasetColumnSpec["dataType"]>;
}

function ActivityRow({
  time,
  title,
  detail,
  state,
}: {
  time: string;
  title: string;
  detail: string;
  state: "complete" | "active";
}) {
  return (
    <div className="activity-row">
      <time>{time}</time>
      <span className={`activity-marker ${state}`} />
      <div>
        <strong>{title}</strong>
        <span>{detail}</span>
      </div>
    </div>
  );
}

type InspectorPanelProps = {
  activeRail: string;
  activeTab: string;
  job: Job | null;
  project: Project;
  preview: TablePreview | null;
  dataset: DatasetVersion | null;
  documentResult: DocumentParseResult | null;
  selectedAsset: Asset | null;
  selectedFile: ProjectFileNode | null;
  selectedAnalysis: string;
  fieldTypes: Record<string, DatasetColumnSpec["dataType"]>;
  onFieldTypeChange: (name: string, dataType: DatasetColumnSpec["dataType"]) => void;
  onTabChange: (tab: string) => void;
};

function InspectorPanel({
  activeRail,
  activeTab,
  job,
  project,
  preview,
  dataset,
  documentResult,
  selectedAsset,
  selectedFile,
  selectedAnalysis,
  fieldTypes,
  onFieldTypeChange,
  onTabChange,
}: InspectorPanelProps) {
  const tabs = [
    { id: "properties", label: "属性" },
    { id: "preview", label: "预览" },
    { id: "changes", label: "变更" },
  ];

  return (
    <aside className="inspector-panel">
      <div className="inspector-tabs" role="tablist" aria-label="检查栏视图">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            aria-selected={activeTab === tab.id}
            data-active={activeTab === tab.id}
            role="tab"
            type="button"
            onClick={() => onTabChange(tab.id)}
          >
            {tab.label}
          </button>
        ))}
      </div>

      <div className="inspector-scroll">
        {activeTab === "preview" ? (
          <>
            <InspectorSection title="当前选择">
              <PropertyRow label="模块" value={railItems.find((item) => item.id === activeRail)?.label ?? "工作台"} />
              <PropertyRow label="文件" value={selectedFile?.name ?? selectedAsset?.name ?? "未选择"} />
              <PropertyRow label="路径" value={selectedFile?.relativePath ?? selectedAsset?.relativePath ?? "不适用"} />
              <PropertyRow label="类型" value={selectedAsset?.mediaType ?? (selectedFile ? "项目文件" : "不适用")} />
              <PropertyRow label="大小" value={selectedAsset ? formatBytes(selectedAsset.size) : selectedFile?.size ? formatBytes(selectedFile.size) : "不适用"} />
            </InspectorSection>
            {documentResult ? <InspectorSection title="页面范围"><PropertyRow label="总页数" value={String(documentResult.pageCount)} /><PropertyRow label="已 OCR" value={String(documentResult.ocrPages.length)} /></InspectorSection> : null}
            {preview ? <InspectorSection title="表格范围"><PropertyRow label="总行数" value={preview.rowCount.toLocaleString("zh-CN")} /><PropertyRow label="字段数" value={String(preview.columnCount)} /></InspectorSection> : null}
          </>
        ) : activeTab === "changes" ? (
          <>
            <InspectorSection title="当前会话变更">
              <InspectorNotice icon={Import} title="文件树已同步" detail="目录、隐藏项和资产关系" />
              <InspectorNotice icon={FileText} title="预览状态已更新" detail={selectedFile?.name ?? selectedAsset?.name ?? "等待选择文件"} />
              <InspectorNotice icon={Box} title="分析配置" detail={analysisMethods.find((item) => item.id === selectedAnalysis)?.label ?? "尚未选择"} />
            </InspectorSection>
          </>
        ) : (
        <>
        {activeRail === "models" ? <InspectorSection title="分析配置">
          <PropertyRow label="方法" value={analysisMethods.find((item) => item.id === selectedAnalysis)?.label ?? "回归"} />
          <PropertyRow label="运行位置" value="本地 Worker" />
          <PropertyRow label="配置状态" value="草稿" />
        </InspectorSection> : null}
        <InspectorSection title="任务状态">
          <PropertyRow label="状态" value={preview ? "等待确认" : job ? statusLabels[job.status] : "尚未开始"} />
          <PropertyRow label="进度" value={preview ? "100%" : job ? `${job.progress}%` : "0%"} />
          <div className="progress-track" aria-label={`任务进度 ${preview ? 100 : job?.progress ?? 0}%`}>
            <span style={{ width: `${preview ? 100 : job?.progress ?? 0}%` }} />
          </div>
          <PropertyRow label="运行位置" value="本地 Worker" />
          <PropertyRow label="更新时间" value="今天 14:33" />
        </InspectorSection>

        {!preview && job ? <InspectorSection title="训练配置">
          <PropertyRow label="任务类型" value="回归" />
          <PropertyRow label="目标列" value="销售额" />
          <PropertyRow label="算法" value="HistGradientBoosting" />
          <PropertyRow label="随机种子" value="42" />
          <PropertyRow label="验证比例" value="15%" />
        </InspectorSection> : null}

        {preview ? (
          <InspectorSection title="导入文件">
            <PropertyRow label="文件名" value={preview.sourceName} />
            <PropertyRow label="格式" value={preview.format.toUpperCase()} />
            <PropertyRow label="编码" value={preview.encoding ?? "不适用"} />
            <PropertyRow label="工作表" value={preview.sheetName ?? "不适用"} />
            <PropertyRow label="行数" value={preview.rowCount.toLocaleString("zh-CN")} />
            <PropertyRow label="字段数" value={String(preview.columnCount)} />
            {dataset ? <PropertyRow label="数据集版本" value={`v${dataset.version}`} /> : null}
          </InspectorSection>
        ) : null}

        {documentResult ? (
          <InspectorSection title="PDF 解析">
            <PropertyRow label="分类" value={documentResult.pdfType} />
            <PropertyRow label="状态" value={documentResult.status} />
            <PropertyRow label="引擎" value={documentResult.engine} />
            <PropertyRow label="页数" value={String(documentResult.pageCount)} />
            <PropertyRow label="OCR 页" value={documentResult.ocrPages.join(", ") || "无"} />
            <PropertyRow label="待 OCR" value={documentResult.pagesNeedingOcr.join(", ") || "无"} />
            <PropertyRow label="JSON" value={documentResult.jsonRelativePath} />
          </InspectorSection>
        ) : null}

        {preview ? (
          <InspectorSection title="字段确认">
            <div className="field-type-list">
              {preview.columns.map((column) => (
                <label key={column.name} className="field-type-row">
                  <span title={column.name}>{column.name}</span>
                  <select
                    value={fieldTypes[column.name] ?? "text"}
                    onChange={(event) => onFieldTypeChange(column.name, event.target.value as DatasetColumnSpec["dataType"])}
                  >
                    <option value="text">文本</option>
                    <option value="integer">整数</option>
                    <option value="number">数值</option>
                    <option value="boolean">布尔值</option>
                  </select>
                </label>
              ))}
            </div>
          </InspectorSection>
        ) : null}

        <InspectorSection title={preview ? "字段概况" : "字段处理"}>
          <InspectorNotice
            icon={Braces}
            title="数值字段"
            detail={preview ? `${preview.columns.filter((column) => isNumericType(column.inferredType)).length} 个字段` : "15 个字段, 使用中位数填充"}
          />
          <InspectorNotice
            icon={FileSpreadsheet}
            title="类别字段"
            detail={preview ? `${preview.columns.filter((column) => !isNumericType(column.inferredType)).length} 个字段` : "9 个字段, 使用序数编码"}
          />
          <InspectorNotice
            icon={BarChart3}
            title="评价指标"
            detail="R2, MAE, RMSE"
          />
        </InspectorSection>

        <InspectorSection title="项目位置">
          <div className="path-value" title={project.path}>
            {project.path}
          </div>
        </InspectorSection>
        </>
        )}
      </div>
    </aside>
  );
}

function InspectorSection({
  title,
  children,
}: {
  title: string;
  children: ReactNode;
}) {
  return (
    <section className="inspector-section">
      <h3>{title}</h3>
      {children}
    </section>
  );
}

function PropertyRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="property-row">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function InspectorNotice({
  icon: Icon,
  title,
  detail,
}: {
  icon: typeof Braces;
  title: string;
  detail: string;
}) {
  return (
    <div className="inspector-notice">
      <Icon aria-hidden="true" size={16} />
      <div>
        <strong>{title}</strong>
        <span>{detail}</span>
      </div>
    </div>
  );
}

type CommandDockProps = {
  activeMode: string;
  prompt: string;
  onModeChange: (mode: string) => void;
  onPromptChange: (value: string) => void;
  onSubmit: () => void;
};

function CommandDock({
  activeMode,
  prompt,
  onModeChange,
  onPromptChange,
  onSubmit,
}: CommandDockProps) {
  return (
    <footer className="command-dock">
      <div className="command-mode" aria-label="命令模式">
        <button
          data-active={activeMode === "task"}
          type="button"
          onClick={() => onModeChange("task")}
        >
          <Sparkles aria-hidden="true" size={14} />
          任务
        </button>
        <button
          data-active={activeMode === "chat"}
          type="button"
          onClick={() => onModeChange("chat")}
        >
          <MessageSquareText aria-hidden="true" size={14} />
          对话
        </button>
      </div>

      <div className="command-input-shell">
        <Bot aria-hidden="true" size={18} />
        <textarea
          aria-label="输入任务或对话内容"
          placeholder={
            activeMode === "task"
              ? "描述需要执行的数据任务"
              : "询问当前项目、数据或模型结果"
          }
          rows={1}
          value={prompt}
          onChange={(event) => onPromptChange(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter" && !event.shiftKey) {
              event.preventDefault();
              onSubmit();
            }
          }}
        />
        <button
          className="run-command-button"
          disabled={!prompt.trim()}
          title="发送"
          type="button"
          onClick={onSubmit}
        >
          <Play aria-hidden="true" size={16} />
          <span className="sr-only">发送</span>
        </button>
      </div>
    </footer>
  );
}

function ResizeHandle() {
  return (
    <PanelResizeHandle className="resize-handle">
      <span />
    </PanelResizeHandle>
  );
}

function formatTime(value: string) {
  return new Intl.DateTimeFormat("zh-CN", {
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  }).format(new Date(value));
}
