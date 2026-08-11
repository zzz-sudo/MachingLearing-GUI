import { useEffect, useMemo, useState } from "react";
import type { Job, Project, ServiceHealth } from "@ml-gui/contracts";
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
  FileSpreadsheet,
  FileText,
  Folder,
  FolderOpen,
  History,
  Import,
  LayoutDashboard,
  ListTree,
  MessageSquareText,
  PanelRightClose,
  Play,
  Search,
  Settings,
  SlidersHorizontal,
  Sparkles,
  Wrench,
} from "lucide-react";
import {
  Panel,
  PanelGroup,
  PanelResizeHandle,
} from "react-resizable-panels";
import { LocalWorkspaceClient } from "./api/localWorkspaceClient";
import { demoJobs, demoProjects } from "./data/demo";

const workspaceClient = new LocalWorkspaceClient();
const initialJob = demoJobs[0]!;
const initialProject = demoProjects[0]!;

const railItems = [
  { id: "workspace", label: "工作台", icon: LayoutDashboard },
  { id: "datasets", label: "数据", icon: Database },
  { id: "documents", label: "文档", icon: FileText },
  { id: "models", label: "模型", icon: Box },
  { id: "jobs", label: "任务", icon: History },
  { id: "tools", label: "工具", icon: Wrench },
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
  const [selectedJobId, setSelectedJobId] = useState(initialJob.id);
  const [prompt, setPrompt] = useState("");
  const [health, setHealth] = useState<ServiceHealth | null>(null);
  const [serviceError, setServiceError] = useState<string | null>(null);

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
  }, []);

  const selectedJob = useMemo(
    () => demoJobs.find((job) => job.id === selectedJobId) ?? initialJob,
    [selectedJobId],
  );

  const selectedProject = initialProject;

  function submitPrompt() {
    const message = prompt.trim();
    if (!message) {
      return;
    }

    setPrompt("");
  }

  return (
    <div className="app-shell">
      <GlobalRail activeItem={activeRail} onChange={setActiveRail} />

      <PanelGroup direction="horizontal" className="workspace-panels">
        <Panel defaultSize={19} minSize={15} maxSize={28}>
          <ContextSidebar
            jobs={demoJobs}
            project={selectedProject}
            selectedJobId={selectedJobId}
            onSelectJob={setSelectedJobId}
          />
        </Panel>

        <ResizeHandle />

        <Panel defaultSize={56} minSize={40}>
          <main className="main-workspace">
            <WorkspaceHeader
              activeRail={activeRail}
              health={health}
              serviceError={serviceError}
            />
            <WorkflowBar job={selectedJob} />
            <WorkspaceContent job={selectedJob} project={selectedProject} />
            <CommandDock
              activeMode={activeMode}
              prompt={prompt}
              onModeChange={setActiveMode}
              onPromptChange={setPrompt}
              onSubmit={submitPrompt}
            />
          </main>
        </Panel>

        <ResizeHandle />

        <Panel defaultSize={25} minSize={20} maxSize={34} collapsible>
          <InspectorPanel
            activeTab={activeInspector}
            job={selectedJob}
            project={selectedProject}
            onTabChange={setActiveInspector}
          />
        </Panel>
      </PanelGroup>
    </div>
  );
}

type GlobalRailProps = {
  activeItem: string;
  onChange: (item: string) => void;
};

function GlobalRail({ activeItem, onChange }: GlobalRailProps) {
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

      <button className="rail-button rail-settings" title="设置" type="button">
        <Settings aria-hidden="true" size={19} strokeWidth={1.8} />
        <span className="sr-only">设置</span>
      </button>
    </nav>
  );
}

type ContextSidebarProps = {
  jobs: Job[];
  project: Project;
  selectedJobId: string;
  onSelectJob: (jobId: string) => void;
};

function ContextSidebar({
  jobs,
  project,
  selectedJobId,
  onSelectJob,
}: ContextSidebarProps) {
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
        <button className="icon-button" title="导入文件" type="button">
          <Import aria-hidden="true" size={17} />
          <span className="sr-only">导入文件</span>
        </button>
      </div>

      <label className="search-box">
        <Search aria-hidden="true" size={15} />
        <input aria-label="搜索项目内容" placeholder="搜索项目内容" />
      </label>

      <section className="sidebar-section">
        <SectionTitle icon={ListTree} title="项目内容" />
        <div className="asset-tree">
          <TreeRow icon={FolderOpen} label="销售预测项目" level={0} open />
          <TreeRow icon={Folder} label="原始文件" level={1} open />
          <TreeRow
            icon={FileSpreadsheet}
            label="华东区域销售数据.xlsx"
            level={2}
          />
          <TreeRow icon={Archive} label="补充资料.zip" level={2} />
          <TreeRow icon={Database} label="销售数据集 v3" level={1} />
          <TreeRow icon={FileText} label="字段说明.pdf" level={1} />
          <TreeRow icon={Box} label="销量回归模型 v2" level={1} />
        </div>
      </section>

      <section className="sidebar-section history-section">
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
      </section>

      <div className="sidebar-footer">
        <span>本地项目</span>
        <span>4 个资产</span>
      </div>
    </aside>
  );
}

type SectionTitleProps = {
  icon: typeof History;
  title: string;
  actionLabel?: string;
};

function SectionTitle({ icon: Icon, title, actionLabel }: SectionTitleProps) {
  return (
    <div className="section-title">
      <span>
        <Icon aria-hidden="true" size={14} />
        {title}
      </span>
      {actionLabel ? (
        <button type="button">{actionLabel}</button>
      ) : null}
    </div>
  );
}

type TreeRowProps = {
  icon: typeof Folder;
  label: string;
  level: number;
  open?: boolean;
};

function TreeRow({ icon: Icon, label, level, open = false }: TreeRowProps) {
  return (
    <button
      className="tree-row"
      style={{ paddingLeft: `${10 + level * 16}px` }}
      title={label}
      type="button"
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

type WorkspaceHeaderProps = {
  activeRail: string;
  health: ServiceHealth | null;
  serviceError: string | null;
};

function WorkspaceHeader({
  activeRail,
  health,
  serviceError,
}: WorkspaceHeaderProps) {
  const activeLabel =
    railItems.find((item) => item.id === activeRail)?.label ?? "工作台";

  return (
    <header className="workspace-header">
      <div className="workspace-title">
        <span className="breadcrumb">销售预测项目 / {activeLabel}</span>
        <h1>华东区域销售数据分析</h1>
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
        <button className="icon-button" title="收起检查栏" type="button">
          <PanelRightClose aria-hidden="true" size={17} />
          <span className="sr-only">收起检查栏</span>
        </button>
      </div>
    </header>
  );
}

function WorkflowBar({ job }: { job: Job }) {
  const steps = ["导入", "字段检查", "训练配置", "模型训练", "结果评估"];
  const activeIndex = job.status === "succeeded" ? 4 : 3;

  return (
    <div className="workflow-bar" aria-label="当前工作流">
      {steps.map((step, index) => (
        <div
          key={step}
          className="workflow-step"
          data-state={
            index < activeIndex
              ? "complete"
              : index === activeIndex
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
  job: Job;
  project: Project;
};

function WorkspaceContent({ job, project }: WorkspaceContentProps) {
  return (
    <div className="workspace-scroll">
      <section className="summary-band">
        <div>
          <span className={`status-dot status-${job.status}`} />
          <div>
            <span className="section-kicker">当前任务</span>
            <h2>{job.title}</h2>
            <p>{job.message}</p>
          </div>
        </div>
        <div className="task-controls">
          <button className="secondary-button" type="button">
            <CircleStop aria-hidden="true" size={15} />
            停止
          </button>
          <button className="primary-button" type="button">
            <Play aria-hidden="true" size={15} />
            继续运行
          </button>
        </div>
      </section>

      <section className="metrics-strip" aria-label="数据集摘要">
        <Metric label="数据行" value="48,216" detail="已过滤 126 行" />
        <Metric label="字段" value="24" detail="数值 15, 类别 9" />
        <Metric label="目标列" value="销售额" detail="回归任务" />
        <Metric label="当前模型" value="HGBR" detail="验证 R2 0.872" />
      </section>

      <section className="content-section">
        <div className="content-heading">
          <div>
            <span className="section-kicker">数据预览</span>
            <h2>销售数据集 v3</h2>
          </div>
          <div className="content-actions">
            <button className="icon-button" title="筛选字段" type="button">
              <SlidersHorizontal aria-hidden="true" size={16} />
              <span className="sr-only">筛选字段</span>
            </button>
            <button className="secondary-button" type="button">
              <FileSpreadsheet aria-hidden="true" size={15} />
              打开数据表
            </button>
          </div>
        </div>

        <div className="data-table-shell">
          <table>
            <thead>
              <tr>
                <th>日期</th>
                <th>区域</th>
                <th>产品类别</th>
                <th>渠道</th>
                <th className="number-cell">销量</th>
                <th className="number-cell">销售额</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td>2026-07-01</td>
                <td>上海</td>
                <td>办公设备</td>
                <td>直营网点</td>
                <td className="number-cell">318</td>
                <td className="number-cell">286,420.00</td>
              </tr>
              <tr>
                <td>2026-07-01</td>
                <td>江苏</td>
                <td>耗材</td>
                <td>电商</td>
                <td className="number-cell">1,284</td>
                <td className="number-cell">174,036.50</td>
              </tr>
              <tr>
                <td>2026-07-02</td>
                <td>浙江</td>
                <td>家具</td>
                <td>经销商</td>
                <td className="number-cell">96</td>
                <td className="number-cell">321,680.00</td>
              </tr>
              <tr>
                <td>2026-07-02</td>
                <td>安徽</td>
                <td>办公设备</td>
                <td>电商</td>
                <td className="number-cell">224</td>
                <td className="number-cell">196,742.00</td>
              </tr>
            </tbody>
          </table>
        </div>
        <div className="table-footer">
          <span>显示前 4 行, 共 48,216 行</span>
          <span>来源: {project.path}</span>
        </div>
      </section>

      <section className="content-section activity-section">
        <div className="content-heading">
          <div>
            <span className="section-kicker">执行记录</span>
            <h2>训练活动</h2>
          </div>
          <button className="text-button" type="button">
            查看完整日志
          </button>
        </div>
        <div className="activity-list">
          <ActivityRow
            time="14:32:18"
            title="训练数据准备完成"
            detail="训练集 33,751 行, 验证集 7,232 行, 测试集 7,233 行"
            state="complete"
          />
          <ActivityRow
            time="14:32:21"
            title="类别字段编码完成"
            detail="处理 9 个类别字段, 未发现未知类别"
            state="complete"
          />
          <ActivityRow
            time="14:33:04"
            title="HistGradientBoosting 训练中"
            detail={`当前进度 ${job.progress}%, 预计剩余 1 分 24 秒`}
            state="active"
          />
        </div>
      </section>
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
  activeTab: string;
  job: Job;
  project: Project;
  onTabChange: (tab: string) => void;
};

function InspectorPanel({
  activeTab,
  job,
  project,
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
        <InspectorSection title="任务状态">
          <PropertyRow label="状态" value={statusLabels[job.status]} />
          <PropertyRow label="进度" value={`${job.progress}%`} />
          <div className="progress-track" aria-label={`任务进度 ${job.progress}%`}>
            <span style={{ width: `${job.progress}%` }} />
          </div>
          <PropertyRow label="运行位置" value="本地 Worker" />
          <PropertyRow label="更新时间" value="今天 14:33" />
        </InspectorSection>

        <InspectorSection title="训练配置">
          <PropertyRow label="任务类型" value="回归" />
          <PropertyRow label="目标列" value="销售额" />
          <PropertyRow label="算法" value="HistGradientBoosting" />
          <PropertyRow label="随机种子" value="42" />
          <PropertyRow label="验证比例" value="15%" />
        </InspectorSection>

        <InspectorSection title="字段处理">
          <InspectorNotice
            icon={Braces}
            title="数值字段"
            detail="15 个字段, 使用中位数填充"
          />
          <InspectorNotice
            icon={FileSpreadsheet}
            title="类别字段"
            detail="9 个字段, 使用序数编码"
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
      </div>
    </aside>
  );
}

function InspectorSection({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
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
