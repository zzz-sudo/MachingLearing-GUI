import { useEffect, useMemo } from "react";
import { BarChart3, ExternalLink, FileImage, FileText } from "lucide-react";
import type { ChartSpec } from "@ml-gui/contracts";

type ChartWorkspaceProps = {
  charts: ChartSpec[];
  selectedChartId: string | null;
  onSelectChart: (chartId: string) => void;
  getChartArtifactUrl: (jobId: string, relativePath: string) => string;
};

const chartTypeLabels: Record<string, string> = {
  scatter: "预测值与真实值", line: "序列趋势", bar: "分类柱状图", histogram: "分布直方图", boxplot: "分组箱线图", heatmap: "相关性热力图", confusion_matrix: "混淆矩阵", feature_importance: "特征重要性", residual: "残差诊断", cluster_scatter: "聚类样本分布", anova_effect: "方差分析效应",
};

const statusLabels: Record<string, string> = { draft: "待生成", queued: "排队中", running: "生成中", succeeded: "已完成", failed: "失败" };

function latestCharts(charts: ChartSpec[]): ChartSpec[] {
  return charts.filter((chart, index, source) => source.findIndex((candidate) => candidate.datasetId === chart.datasetId && candidate.name === chart.name && candidate.chartType === chart.chartType) === index);
}

function artifactLocation(chart: ChartSpec | null, suffix: string): { jobId: string; relativePath: string } | null {
  const artifactId = chart?.artifactIds.find((artifact) => artifact.endsWith(`:${suffix}`));
  if (!artifactId) return null;
  const separator = artifactId.indexOf(":");
  return separator > 0 ? { jobId: artifactId.slice(0, separator), relativePath: artifactId.slice(separator + 1) } : null;
}

export function ChartWorkspace({ charts, selectedChartId, onSelectChart, getChartArtifactUrl }: ChartWorkspaceProps) {
  const visibleCharts = useMemo(() => latestCharts(charts), [charts]);
  const selectedChart = visibleCharts.find((chart) => chart.id === selectedChartId) ?? visibleCharts[0] ?? null;
  const image = artifactLocation(selectedChart, "chart.png");
  const html = artifactLocation(selectedChart, "chart.html");

  useEffect(() => {
    if (selectedChart && selectedChart.id !== selectedChartId) onSelectChart(selectedChart.id);
  }, [onSelectChart, selectedChart, selectedChartId]);

  return (
    <div className="workspace-scroll chart-workspace">
      <section className="chart-intro-band"><div><span className="section-kicker">模型结果图形</span><h2>{selectedChart ? selectedChart.name : "等待模型生成图形"}</h2><p>图形由当前模型的诊断规格生成。选择左侧图形后，右侧只展示对应结果和可下载产物。</p></div><div><span>当前结果</span><strong>{visibleCharts.length}</strong></div></section>
      <div className="chart-result-layout">
        <aside className="chart-result-list" aria-label="模型图形列表"><div className="chart-list-heading"><span>图形目录</span><strong>{visibleCharts.length}</strong></div>{visibleCharts.length === 0 ? <div className="chart-empty-state compact"><BarChart3 aria-hidden="true" size={25} /><strong>训练完成后显示模型图形</strong><span>模型会根据任务类型生成推荐诊断图。</span></div> : visibleCharts.map((chart) => <button className={chart.id === selectedChart?.id ? "chart-result-item active" : "chart-result-item"} key={chart.id} type="button" onClick={() => onSelectChart(chart.id)}><BarChart3 aria-hidden="true" size={17} /><span><strong>{chart.name}</strong><small>{chartTypeLabels[chart.chartType] ?? chart.chartType}</small></span><em data-status={chart.status}>{statusLabels[chart.status] ?? chart.status}</em></button>)}</aside>
        <section className="chart-result-view" aria-live="polite">{selectedChart ? <><header className="chart-result-header"><div><span className="section-kicker">{chartTypeLabels[selectedChart.chartType] ?? selectedChart.chartType}</span><h2>{selectedChart.name}</h2><p>{statusLabels[selectedChart.status] ?? selectedChart.status}</p></div><div className="chart-result-actions">{image ? <a className="artifact-download-button primary" href={getChartArtifactUrl(image.jobId, image.relativePath)} download><FileImage aria-hidden="true" size={14} />保存生成图形</a> : null}{html ? <a className="artifact-download-button" href={getChartArtifactUrl(html.jobId, html.relativePath)} download><ExternalLink aria-hidden="true" size={14} />下载交互图形</a> : null}</div></header>{image ? <div className="chart-result-image-frame"><img src={getChartArtifactUrl(image.jobId, image.relativePath)} alt={`${selectedChart.name} 图形`} /></div> : <div className="chart-empty-state"><FileText aria-hidden="true" size={30} /><strong>{statusLabels[selectedChart.status] ?? selectedChart.status}</strong><span>图形 Worker 完成后，静态预览会自动出现。</span></div>}</> : <div className="chart-empty-state"><BarChart3 aria-hidden="true" size={34} /><strong>尚未选择模型图形</strong><span>完成一次模型训练后，诊断图会出现在这里。</span></div>}</section>
      </div>
    </div>
  );
}
