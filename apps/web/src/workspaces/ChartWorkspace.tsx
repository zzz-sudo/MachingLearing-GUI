import { useEffect, useState } from "react";
import { BarChart3, Download, ExternalLink } from "lucide-react";
import type { ChartGenerationResult, ChartSpec, ChartSpecCreate, DatasetVersion, TablePreview } from "@ml-gui/contracts";

type ChartWorkspaceProps = {
  dataset: DatasetVersion | null;
  preview: TablePreview | null;
  charts: ChartSpec[];
  onCreateChart: (payload: ChartSpecCreate) => Promise<ChartSpec>;
  onGenerateChart: (chartId: string) => Promise<ChartGenerationResult>;
  onGetChartResult: (jobId: string) => Promise<ChartGenerationResult>;
  getChartArtifactUrl: (jobId: string, relativePath: string) => string;
};

function ChartProperty({ label, value }: { label: string; value: string }) {
  return <div className="property-row"><span>{label}</span><strong>{value}</strong></div>;
}

export function ChartWorkspace({ dataset, preview, charts, onCreateChart, onGenerateChart, onGetChartResult, getChartArtifactUrl }: ChartWorkspaceProps) {
  const columns = dataset?.columns ?? [];
  const numericColumns = columns.filter((column) => ["integer", "number"].includes(column.dataType));
  const [name, setName] = useState("数据分布图");
  const [chartType, setChartType] = useState<ChartSpecCreate["chartType"]>("scatter");
  const [xColumn, setXColumn] = useState("");
  const [yColumns, setYColumns] = useState<string[]>([]);
  const [generation, setGeneration] = useState<ChartGenerationResult | null>(null);
  const [generating, setGenerating] = useState(false);
  const [selectedSavedChartId, setSelectedSavedChartId] = useState<string | null>(null);

  useEffect(() => {
    setXColumn((current) => current || numericColumns[0]?.name || columns[0]?.name || "");
    setYColumns((current) => current.length > 0 ? current : [numericColumns[1]?.name || numericColumns[0]?.name || ""].filter(Boolean));
  }, [dataset?.id, numericColumns.length, columns.length]);

  // Keep the latest chart for the same dataset and chart type in the primary view.
  // Historical jobs remain persisted and can be revisited from the job history.
  const visibleCharts = charts.filter((chart, index, source) => source.findIndex((candidate) => candidate.datasetId === chart.datasetId && candidate.name === chart.name && candidate.chartType === chart.chartType) === index);
  const savedCharts = visibleCharts.filter((chart) => chart.status === "succeeded" && chart.artifactIds.length > 0);
  useEffect(() => {
    setSelectedSavedChartId((current) => current && savedCharts.some((chart) => chart.id === current) ? current : savedCharts[0]?.id ?? null);
  }, [charts]);

  const selectedSavedChart = savedCharts.find((chart) => chart.id === selectedSavedChartId) ?? null;
  const savedArtifactId = selectedSavedChart?.artifactIds.find((artifact) => artifact.endsWith(":chart.html")) ?? selectedSavedChart?.artifactIds[0] ?? "";
  const savedArtifactSeparator = savedArtifactId.indexOf(":");
  const savedJobId = savedArtifactSeparator > 0 ? savedArtifactId.slice(0, savedArtifactSeparator) : "";
  const savedRelativePath = savedArtifactSeparator > 0 ? savedArtifactId.slice(savedArtifactSeparator + 1) : "";

  const rows = preview?.rows ?? [];
  const yColumn = yColumns[0] ?? "";
  const requiresXAxis = ["scatter", "line", "bar"].includes(chartType);
  const requiresSingleY = chartType === "histogram";
  const values = rows.map((row) => Number(row[yColumn])).filter((value) => Number.isFinite(value)).slice(0, 24);
  const maxValue = Math.max(...values, 1);

  async function saveAndGenerate() {
    const chart = await onCreateChart({ name: name.trim(), chartType, datasetId: dataset!.id, xColumn: requiresXAxis ? xColumn : null, yColumns: requiresSingleY ? yColumns.slice(0, 1) : yColumns, options: { theme: "cns", showLegend: true, palette: "cns-safe" } });
    setGenerating(true);
    try {
      const queued = await onGenerateChart(chart.id);
      setGeneration(queued);
      if (queued.status === "queued" || queued.status === "running") {
        const timer = window.setInterval(() => {
          void onGetChartResult(queued.jobId).then((result) => {
            setGeneration(result);
            if (["succeeded", "failed", "cancelled"].includes(result.status)) {
              window.clearInterval(timer);
              setGenerating(false);
            }
          }).catch(() => undefined);
        }, 1000);
        window.setTimeout(() => {
          window.clearInterval(timer);
          setGenerating(false);
        }, 3600000);
      } else {
        setGenerating(false);
      }
    } catch {
      setGenerating(false);
    }
  }

  return (
    <div className="workspace-scroll chart-workspace">
      <section className="chart-intro-band">
        <div><span className="section-kicker">图形工作区</span><h2>从数据和模型结果生成可追溯图形</h2><p>图形规格会保存数据集版本、字段映射和样式选项，刷新后可以继续编辑。</p></div>
        <div><span>已保存图形</span><strong>{charts.length}</strong></div>
      </section>
      <div className="chart-workspace-grid">
        <section className="chart-canvas-section">
          <div className="section-heading"><div><span className="section-kicker">实时预览</span><h2>{name}</h2></div><span>{dataset ? `数据集 v${dataset.version}` : "等待数据集"}</span></div>
          {visibleCharts.length > 0 ? <div className="saved-chart-panel"><div className="saved-chart-heading"><span>已生成图形</span><strong>{savedCharts.length}/{visibleCharts.length}</strong></div><div className="saved-chart-list">{visibleCharts.map((chart) => <button className={chart.id === selectedSavedChartId ? "saved-chart-item active" : "saved-chart-item"} key={chart.id} type="button" onClick={() => setSelectedSavedChartId(chart.id)}><span>{chart.name}</span><small>{chart.status}</small></button>)}</div>{selectedSavedChart && savedJobId && savedRelativePath ? <div className="saved-chart-preview"><img className="chart-image-preview" src={getChartArtifactUrl(savedJobId, "chart.png")} alt={`${selectedSavedChart.name} 静态预览`} /><div className="chart-artifact-toolbar"><span>静态预览</span><a className="artifact-download-button" href={getChartArtifactUrl(savedJobId, "chart.html")} target="_blank" rel="noreferrer"><ExternalLink aria-hidden="true" size={14} />打开交互图形</a></div></div> : <p className="chart-empty-hint">训练完成后，诊断图会在这里显示。</p>}</div> : null}
          {values.length > 0 ? <div className="chart-preview-bars" aria-label="图形预览">{values.map((value, index) => <div key={`${value}-${index}`} className="chart-preview-bar" style={{ height: `${Math.max(8, value / maxValue * 100)}%` }}><span>{value.toFixed(0)}</span></div>)}</div> : <div className="chart-empty-state"><BarChart3 aria-hidden="true" size={30} /><strong>选择数据集后预览图形</strong><span>当前预览使用前 24 条可见记录。</span></div>}
        </section>
        <section className="chart-config-section">
          <div className="section-heading"><div><span className="section-kicker">图形设计</span><h2>字段映射</h2></div></div>
          <div className="chart-config-form">
            <label><span>名称</span><input value={name} onChange={(event) => setName(event.target.value)} /></label>
            <label><span>图形类型</span><select value={chartType} onChange={(event) => setChartType(event.target.value as ChartSpecCreate["chartType"])}><option value="scatter">散点图</option><option value="line">折线图</option><option value="bar">柱状图</option><option value="histogram">直方图</option><option value="boxplot">箱线图</option><option value="heatmap">相关性热力图</option></select></label>
            <label><span>X 轴</span><select disabled={!requiresXAxis} value={requiresXAxis ? xColumn : ""} onChange={(event) => setXColumn(event.target.value)}><option value="">{requiresXAxis ? "请选择字段" : "当前图形不使用 X 轴"}</option>{requiresXAxis ? columns.map((column) => <option key={column.name} value={column.name}>{column.name}</option>) : null}</select></label>
            <label><span>{requiresSingleY ? "Y 轴字段" : "Y 轴字段"}</span><select multiple={!requiresSingleY} size={requiresSingleY ? 1 : Math.min(5, Math.max(2, numericColumns.length))} value={requiresSingleY ? yColumns.slice(0, 1) : yColumns} onChange={(event) => setYColumns(Array.from(event.target.selectedOptions, (option) => option.value))}>{numericColumns.map((column) => <option key={column.name} value={column.name}>{column.name}</option>)}</select></label>
            <div className="chart-source-summary"><ChartProperty label="数据集" value={dataset ? `v${dataset.version}` : "未选择"} /><ChartProperty label="来源字段" value={`${xColumn || "未选择"} / ${yColumns.join(", ") || "未选择"}`} /><ChartProperty label="预览记录" value={String(rows.length)} /></div>
            <button className="primary-button" disabled={generating || !dataset || (requiresXAxis && !xColumn) || yColumns.length === 0 || !name.trim()} type="button" onClick={() => void saveAndGenerate()}><BarChart3 aria-hidden="true" size={15} />{generating ? "正在生成" : "保存并生成图形"}</button>
            {generation ? <div className="chart-generation-state"><ChartProperty label="任务状态" value={generation.status} />{generation.errorMessage ? <p className="chart-generation-error">{generation.errorType}: {generation.errorMessage}</p> : null}{generation.warnings.map((warning) => <p key={warning}>{warning}</p>)}{generation.status === "succeeded" && generation.jobId ? <div className="chart-artifact-preview"><div className="chart-artifact-toolbar"><span>静态预览</span><a className="artifact-download-button" href={getChartArtifactUrl(generation.jobId, "chart.html")} target="_blank" rel="noreferrer"><ExternalLink aria-hidden="true" size={14} />打开交互图形</a></div><img className="chart-image-preview" src={getChartArtifactUrl(generation.jobId, "chart.png")} alt="当前图形静态预览" /></div> : null}{generation.artifacts.map((artifact) => <a className="artifact-download-button" key={artifact.relativePath} href={getChartArtifactUrl(generation.jobId, artifact.relativePath)} download><Download aria-hidden="true" size={14} />下载 {artifact.format.toUpperCase()}</a>)}</div> : null}
          </div>
        </section>
      </div>
    </div>
  );
}
