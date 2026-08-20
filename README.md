# MachingLearing GUI

作者: Kuroneko

功能: 本地优先的数据导入、文档解析、字段确认、数据集版本管理、机器学习训练和结果导出工作台。

输入文件: csv, xlsx, pdf, zip, tar, tgz, gz。后续扩展 docx, pptx, md, html, parquet 和常用图片格式。

输出文件: Parquet 数据集、DOCX、XLSX、Markdown、TXT、JSON 结构化结果、模型文件、预测文件和 Windows 桌面程序。

## 项目说明

本项目用于构建一个本地优先的数据解析和机器学习桌面工作台。用户可以导入表格、文档和压缩文件，在统一界面中完成文件解析、数据检查、数据清洗、模型训练、结果预览和文件导出。桌面版本优先支持 Windows，后续复用同一套前端和接口扩展为本地 Web 版本及云端版本。

当前仓库已经进入可运行原型阶段，包含 React 工作台、Python Task Service 和 Tauri 桌面外壳。本文件是当前仓库唯一需要维护的 Markdown 文档。

## 输入文件格式

第一阶段规划支持以下输入格式。

- 表格文件: csv, xls, xlsx, ods, parquet
- 文档文件: pdf, docx, pptx, txt, md, html
- 图片文件: png, jpg, jpeg, tif, tiff
- 压缩文件: zip, 7z, tar, gz

压缩文件导入后必须先解压到项目隔离目录，再按照解压后文件的实际格式进入对应解析流程。原始压缩文件和解压后的文件都需要记录来源关系。

## 输出文件类型

项目规划输出以下类型的文件或目录。

- 数据文件: csv, xlsx, parquet
- 文档文件: md, html, pdf
- 模型文件: joblib, pkl, onnx
- 预测结果: csv, xlsx, parquet
- 项目元数据: json, sqlite
- 训练记录: json, csv, html
- 日志文件: log
- Windows 分发文件: exe 安装程序和应用目录

## 脚本和应用功能

最终应用负责完成以下工作。

1. 创建和管理本地项目工作区。
2. 导入普通文件或压缩文件。
3. 解析 PDF、XLSX、CSV 和其他受支持文件。
4. 检查文件编码、字段类型、空值、重复值和异常值。
5. 将解析结果转换为可复用的数据集或文档资产。
6. 配置并执行分类、回归等机器学习任务。
7. 保存训练参数、随机种子、依赖版本、指标和模型文件。
8. 通过统一界面预览数据、文档、模型结果和文件变更。
9. 通过 OpenClaw 对话窗口查询项目内容并申请执行受控工具。
10. 在本地桌面、本地 Web 和未来云端环境中复用相同的业务接口。

## 基础限制

- 界面和文档禁止使用表情、对号、叉号及装饰性特殊符号。
- 中文用于产品文档、界面文案和详细业务说明。
- 源代码注释统一使用英文 comment。
- 关键算法、数据流、外部接口和不直观的处理必须有详细中文设计说明。
- 项目模块之间保持必要耦合，通过稳定的数据模型、任务接口和资产标识协同工作。
- 避免无意义的防御性代码。文件输入、外部工具、模型执行和网络调用等真实边界必须返回明确的错误类型和错误信息。
- GUI 使用稳定尺寸、可调整面板和统一间距，避免文字、按钮、表格和预览区域错位。
- 所有上传、导入、解析、解压、训练和导出操作必须留下可追溯记录。

## 总体构建方案

项目采用本地优先、接口统一、执行环境可切换的构建方式。桌面端、本地 Web 和云端 Web 共用 React 前端和 Workspace API。执行任务时，由运行环境选择本地 Python 服务或云端 Worker，不在界面组件中直接调用解析器和模型库。

整体结构如下。

```text
React and TypeScript Workspace UI
        |
Workspace Client Contract
        |
Local Runtime or Cloud Runtime
        |
Python Task Service
        |
Parser, Dataset, Training and Export Modules
        |
SQLite, DuckDB, Parquet and Artifact Files
```

桌面版使用 Tauri 承载 React 界面，并把 Python 服务作为 sidecar 随安装包发布。本地 Web 版直接在浏览器打开相同的 React 应用，并连接运行在本机回环地址的 Python 服务。云端版继续使用相同的 Workspace Client Contract，但把服务地址切换到云端 API。

## 本地 Python 环境选择

本机当前存在以下 Python 目录。

- D:\Python\python11
- D:\Python\Python314
- D:\Python\Python38
- D:\Python\Python39

默认开发环境选择 D:\Python\python11。该环境为 Python 3.11，并已检测到 PyTorch 和 TensorFlow 包。第一版选择 PyTorch 作为深度学习扩展框架，传统表格模型仍优先使用 scikit-learn。

正式构建前必须执行独立的 CUDA 能力检查，验证 PyTorch 版本、CUDA 版本、显卡可用性和 SM120 架构支持。检查失败时需要输出错误类型、PyTorch 版本、CUDA 版本和检测到的计算架构，不允许静默切换到错误设备。CPU 模式可以作为用户明确选择的运行模式，但不作为隐藏回退逻辑。

## 运行时设计

运行时分为界面进程、桌面主进程、任务服务和任务 Worker。

- 界面进程只处理交互、状态展示、表格虚拟滚动、文档预览和结果展示。
- Tauri 主进程负责窗口、文件选择、应用目录、凭据访问和 Python sidecar 生命周期。
- Python Task Service 负责项目接口、文件导入、任务创建、进度事件和结果查询。
- Worker 负责解压、解析、数据清洗、特征处理、模型训练、预测和导出。

耗时任务必须在 Worker 中运行。界面通过任务状态和进度事件更新，不直接等待训练函数返回。统一任务状态包括 queued, running, waiting_confirmation, succeeded, failed 和 cancelled。

## 项目存储设计

每个项目使用独立目录，建议结构如下。

```text
project-root
  project.json
  metadata.sqlite
  source
  extracted
  datasets
  documents
  models
  predictions
  reports
  logs
  temp
```

- source 保存用户导入的原始文件，导入后默认只读。
- extracted 保存压缩文件解压结果和文档解析中间文件。
- datasets 保存 Parquet 数据和字段定义。
- documents 保存结构化 JSON、Markdown、页级索引和表格结果。
- models 保存模型文件、训练参数、指标和依赖清单。
- predictions 保存批量预测结果。
- reports 保存用户导出的报告。
- metadata.sqlite 保存项目、资产、任务、关系和审计记录。
- temp 只保存可重建的临时文件，应用正常退出或任务回收时清理。

SQLite 用于业务元数据，DuckDB 用于本地查询和统计，Parquet 用于标准化表格资产。不得把完整大型表格直接存入界面状态或 SQLite 单元格。

## GUI 布局设计

主窗口采用图标栏、左侧上下文栏、中间工作区、右侧检查栏和底部命令区。

### 全局图标栏

全局图标栏保持固定宽度，包含项目、数据、文档、模型、任务、工具和设置入口。按钮只显示统一尺寸图标，并通过 tooltip 提供名称。当前模块使用背景和边框状态区分，不改变按钮尺寸。

### 左侧上下文栏

左侧栏显示当前模块的项目树、文件、数据集、模型版本或任务历史。宽度允许拖动调整，但需要设置最小宽度和最大宽度。树节点使用固定行高，长文件名截断显示并通过 tooltip 查看完整名称。

### 中间工作区

中间区域是主要操作空间，根据资产类型显示数据表格、PDF 页面、训练配置、训练日志、指标图表、预测结果或报告。固定格式内容使用稳定的容器尺寸和滚动区域，加载状态、空状态和错误状态不能改变整体布局尺寸。

### 右侧检查栏

右侧栏显示当前选择对象的属性、字段映射、解析设置、训练参数、文件预览、模型指标和变更记录。右侧栏可以折叠，折叠按钮使用固定图标，不使用文字胶囊按钮。

### 底部命令区

底部命令区固定在工作区底部，包含任务状态、运行控制、模式选择和 OpenClaw 对话输入。输入框高度允许有限范围增长，不能覆盖中间结果区。运行、停止、导入和导出使用图标加 tooltip，模式选择使用 segmented control。

### 对齐规则

- 所有工具栏使用统一高度和内边距。
- 所有图标按钮使用固定宽高，不因加载状态或文字变化而移动。
- 面板标题、操作按钮和关闭按钮使用固定网格列。
- 表格使用虚拟滚动和固定表头，列宽调整不能推动外层布局。
- 中文长文本允许换行，文件名和标识符使用省略显示。
- 弹窗内容设置最大高度和内部滚动，禁止超出屏幕。
- 在 1366 x 768, 1920 x 1080 和高 DPI 缩放环境中执行截图检查。
- 桌面版和 Web 版共用布局断点，但桌面最小窗口尺寸需要限制在可用工作区范围内。

### 当前文件树和文档工作区

项目内容栏通过 Task Service 读取真实项目目录，不使用前端写死的示例节点。目录优先于文件排序，支持层级展开、名称搜索、隐藏文件显示和隐藏、长文件名省略显示。Windows 隐藏属性和以点开头的隐藏项都进入同一套显示规则。目录遍历不跟随符号链接，文件内容接口还会再次检查最终路径是否仍在当前项目根目录内。

点击已导入的 CSV 或 XLSX 会进入数据工作区并恢复表格预览。点击已解析 PDF 会进入文档工作区，原文件视图使用完整可滚动页面，解析内容视图按全部页展示 OCR 或文本提取结果。点击项目中的 JSON、Markdown、TXT 和其他普通文件会进入只读原文件预览。浏览器本身不能直接渲染的 Office 二进制格式需要先走解析器，不能把在线 Office Viewer 作为本地离线功能的必要依赖。

PDF 解析结果可以导出以下格式。

- DOCX: 按页写入标题和正文，适合继续在 Word 中编辑。
- XLSX: 包含摘要工作表和逐页内容工作表，适合后续数据整理。
- Markdown: 保留页级标题和完整解析文本。
- TXT: 使用 UTF-8 编码保存逐页纯文本，避免中文乱码。

### 当前模型工作区

模型模块按任务选择、任务设计、训练监控和评估结果组织，不把所有算法参数堆叠在同一页面。第一层先选择分类、回归、方差分析、聚类或深度学习，第二层再配置数据集版本、目标字段、验证集比例、随机种子和 CPU 或 GPU 运行位置。训练监控和评估结果使用独立标签页，为后续 Worker 进度、指标图表、混淆矩阵、残差图和产物下载保留稳定区域。

模型任务只有在用户确认字段并创建数据集版本后才能启动。启动后服务端创建 Job，单独的本地 Python Worker 读取 Parquet 数据集、按随机种子抽样、执行训练、保存模型产物，并把真实状态和指标写回项目目录。界面只展示 Worker 返回的 queued, running, succeeded 或 failed 状态，不伪造训练进度和评估指标。

传统分类和回归使用 scikit-learn，聚类使用 KMeans，方差分析使用 scipy，深度学习使用本机 PyTorch。默认会使用 `D:\Python\python11\python.exe` 运行训练 Worker，因为该环境已经包含适配本机显卡的 PyTorch、scikit-learn、pandas、PyArrow 和 SciPy。可通过 `ML_GUI_TRAINING_PYTHON` 指定其他 Python 3.11 环境。GPU 被用户明确选择但不可用时，Worker 返回训练错误，不会静默改用 CPU。

训练产物保存为 `models/<job_id>/model.joblib`、`model.pt` 或 `anova.json`，同目录的 `run.json` 保存输入配置，`result.json` 保存状态、指标、目标字段和产物路径。这些文件与 DatasetVersion、Job 和 Asset 标识相互关联，保证训练结果可追踪。

#### 综合算法目录

算法能力不能继续通过分类、回归、聚类、方差分析和深度学习五个模糊字符串表达。服务端现在提供 `GET /api/algorithms` 作为算法目录的单一事实来源。目录中的每个算法都有稳定的 `algorithmId`、任务类型、算法族、数据要求、GPU 能力和参数定义。界面后续只根据该目录生成可用算法和参数控件，不在前端复制另一套容易过期的算法清单。

当前目录覆盖以下能力范围。

- 表格分类: 逻辑回归、决策树、随机森林、极端随机树、直方图梯度提升和 XGBoost。
- 表格回归: 线性回归、岭回归、随机森林、极端随机树、直方图梯度提升和 XGBoost。
- 聚类: K-Means、MiniBatch K-Means、层次聚类、DBSCAN、HDBSCAN、高斯混合模型和 BIRCH。
- 统计分析: 单因素方差分析以及包含主效应和交互效应的多因素方差分析。
- 序列深度学习: 用于序列回归和序列分类的 RNN、LSTM 和 GRU。

算法目录只表示计划由当前运行时正式支持的能力，不代表仅仅显示一个界面按钮。算法进入可发布状态前必须同时具备 Runner、输入校验、指标计算、产物保存、产物重载和项目内测试数据。尚未完成这些闭环的算法不能在任务提交界面中标记为可执行。

多因素方差分析在本项目中表示 factorial ANOVA，不等同于多个因变量的 MANOVA。序列算法要求用户明确选择时间字段、目标字段、特征字段、窗口长度和预测步长，并使用按时间顺序切分的数据，禁止沿用普通表格任务的随机切分方式。

监督学习 Runner 已经实现逻辑回归、决策树分类、随机森林分类和回归、极端随机树分类和回归、直方图梯度提升分类和回归、线性回归、岭回归以及 XGBoost 分类和回归。训练请求可以指定特征字段和算法超参数。Worker 会根据训练数据自动建立数值缺失值填充和标准化、类别缺失值填充和 One-Hot 编码，并把预处理 Pipeline、模型和分类目标编码器一起保存为 `model.joblib`。

分类结果包含 accuracy、balanced accuracy、weighted precision、weighted recall、weighted F1、可用时的 log loss、混淆矩阵和特征重要性。回归结果包含 MAE、MSE、RMSE、R squared、残差预览和特征重要性。`result.json` 同时保存算法 ID、实际特征顺序、规范化超参数、依赖版本和产物清单。自动测试会训练每个监督学习算法、重新加载产物并比较加载前后的预测结果。

Task Service 的基础环境和训练环境继续分离。`pyproject.toml` 的 `training` extra 声明传统机器学习和统计分析依赖。PyTorch 需要依据目标设备和 CUDA 版本单独安装，不能由普通 PyPI 依赖在所有设备上隐式选择。训练 Worker 默认使用 `D:\Python\python11\python.exe`，也可以通过 `ML_GUI_TRAINING_PYTHON` 指向具备所需算法依赖的 Python 3.11 环境。

聚类 Runner 已经实现 K-Means、MiniBatch K-Means、层次聚类、DBSCAN、HDBSCAN、高斯混合模型和 BIRCH。所有聚类算法共用字段选择、缺失值处理、类别编码和标准化过程，并输出聚类数量、噪声数量、噪声比例以及条件允许时的 Silhouette、Calinski-Harabasz 和 Davies-Bouldin 指标。`clusterSummary` 记录各聚类的样本数和比例，`sampleAssignments` 提供最多 500 条可预览的样本分配。

聚类产物保存预处理器、模型、特征顺序和全部训练标签。K-Means、高斯混合模型等支持对新样本执行预测的算法保留模型自身的 `predict` 能力。层次聚类、DBSCAN 和 HDBSCAN 不具有与训练过程等价的通用新样本预测接口，因此产物通过 `supportsPrediction` 明确标记能力，并保存训练标签供结果恢复，不能在推理界面伪造预测功能。

### 真实案例数据

开发运行时示例目录使用公开数据，不把大体积第三方文件提交到 Git 仓库。下载和导入完成后，真实资产会出现在当前项目的 `source` 目录，经过字段确认后再创建 Parquet 数据集。

- UCI Online Retail: 原始 XLSX 交易数据，541,909 条记录和 8 个字段。该数据集用于字段类型确认、缺失值处理、聚类和回归流程，来源为 UCI Machine Learning Repository，采用 CC BY 4.0。
- Attention Is All You Need: arXiv 1706.03762 原始论文 PDF，共 15 页，用于文本层 PDF、逐页预览、Markdown 和 DOCX、XLSX、TXT 导出流程。
- Our World in Data CO2 Data README: 原始 Markdown 文档，用于应用内 Markdown 阅读器和 UTF-8 文本预览流程。

来源地址分别为 `https://archive.ics.uci.edu/static/public/352/online+retail.zip`、`https://arxiv.org/pdf/1706.03762.pdf` 和 `https://github.com/owid/co2-data`。使用公开数据时仍需保留来源和许可证信息，不能把案例数据误标为应用自行生成的数据。

## 文件导入和乱码处理

桌面端中的上传统一称为导入。导入层必须保留原始文件名、原始字节、文件大小、修改时间、来源路径和内容哈希。

文本和 CSV 编码处理顺序如下。

1. 检查 UTF-8 BOM, UTF-16 LE BOM 和 UTF-16 BE BOM。
2. 尝试严格 UTF-8 解码。
3. 对中文环境尝试 GB18030。
4. 使用编码检测库提供候选编码和置信度。
5. 低置信度或多种编码都可解析时，要求用户在预览窗口确认。
6. 内部文本统一转换为 UTF-8，导出时允许用户选择 UTF-8 BOM 或原始兼容编码。

CSV 解析还需要检测分隔符、引号字符、换行类型和表头行。乱码修复不能通过忽略非法字节实现。解析失败必须保留原文件并输出 FileEncodingError，错误信息包含文件名、尝试过的编码和失败位置。

ZIP 文件名可能使用 UTF-8、CP437 或本地代码页。解压模块必须读取 ZIP 标志位，并为无法可靠判断的文件名提供解压预览。禁止把乱码文件名直接写入最终项目资产。

## 核心数据模型和必要耦合

项目不追求模块完全独立。解析、数据集、训练、预测、报告和 OpenClaw 工具必须围绕统一的 Project, Asset, Job 和 Artifact 数据模型协同工作，这属于必要耦合。

- Project 表示一个完整工作空间。
- Asset 表示用户导入的原始文件或外部资源。
- Artifact 表示解析、转换、训练或导出的产物。
- DatasetVersion 表示不可变的数据集版本。
- DocumentVersion 表示不可变的文档解析版本。
- ModelRun 表示一次可复现的训练执行。
- Job 表示一个可排队、可取消、可追踪的执行任务。
- ToolDefinition 表示可被 GUI 或 OpenClaw 调用的受控能力。

所有模块共享以上标识和状态定义，但解析器、训练器和导出器不得直接依赖 React 组件、Tauri 窗口或 OpenClaw 内部对象。界面通过 Workspace Client Contract 调用任务服务，任务服务通过 ToolDefinition 调度具体实现。

## 工具契约

左侧工具栏中的每个工具都必须声明以下内容。

- tool_id: 稳定工具标识。
- name: 中文显示名称。
- input_types: 允许输入的资产类型。
- output_types: 可能产生的 Artifact 类型。
- parameter_schema: 用于生成参数表单的结构定义。
- execution_target: local, cloud 或 both。
- permission_level: read, create, modify, external 或 compute。
- implementation_version: 实现版本。
- timeout_policy: 超时和取消策略。
- error_types: 可能返回的公开错误类型。

工具结果必须返回结构化数据，不允许只返回日志字符串。日志用于诊断，Artifact 用于后续业务流程。

第一阶段工具包括以下内容。

1. 导入文件。
2. 解压文件。
3. 解析 CSV。
4. 解析 XLSX。
5. 解析 PDF。
6. 数据剖析。
7. 数据清洗。
8. 配置分类任务。
9. 配置回归任务。
10. 训练模型。
11. 批量预测。
12. 导出数据。
13. 生成模型报告。
14. 查询项目上下文。

## 导入和解压流程

文件导入按以下顺序执行。

1. 复制原始文件到 source 目录。
2. 计算 SHA-256 内容哈希并记录来源信息。
3. 根据文件签名和扩展名判断实际格式。
4. 如果是压缩文件，创建独立 extracted 子目录并解压。
5. 对解压文件重新执行格式检测，支持压缩包内嵌套压缩文件，但限制最大嵌套层数。
6. 对每个文件建立 Asset 记录并关联父压缩文件。
7. 根据文件类型进入表格、文档、图片或未知文件流程。

解压是必须保留的真实安全边界。需要防止路径穿越、覆盖已有文件、符号链接逃逸、异常压缩比和超大文件。此处允许必要的防御性代码，并返回 ArchiveExtractionError。普通内部函数不重复进行无意义的空值和类型检查。

## XLSX 和表格解析设计

XLSX 不能只按文本文件处理。导入后先读取工作簿结构，再由用户确认用于分析的 Sheet、表头行和数据区域。

解析结果需要包含以下内容。

- Sheet 名称和顺序。
- 使用区域和隐藏状态。
- 表头候选行。
- 字段名称、推断类型和示例值。
- 空值、重复值和唯一值统计。
- 公式单元格、合并单元格和错误单元格信息。
- 日期、货币、百分比和本地化数字格式。
- 数据量和预计内存占用。

普通 XLSX 元数据和兼容处理使用 openpyxl。大规模表格读取优先评估 Polars 和基于 Rust 的读取实现。转换后的标准数据集保存为 Parquet，原始工作簿保持不变。

公式默认读取文件中保存的计算结果，不在第一版中实现完整 Excel 公式引擎。包含宏的 xlsm 文件只能作为受限输入处理，不执行宏。旧版 xls 通过专用转换器读取，并在界面中标记转换来源。

## PDF 和文档解析设计

PDF 需要先分类再解析，不能把所有文件交给同一个高成本 OCR 流程。当前实现先使用 PyMuPDF 检查每一页的文本层。存在足够文本层的页面直接提取，缺少文本层的页面渲染为二倍分辨率图像，再交给 RapidOCR 的本地 ONNX 模型识别。文档最终分类为 text_based, scanned 或 mixed，并分别记录 ocrPages 和 pagesNeedingOcr。前者表示已经执行 OCR 的页面，后者表示 OCR 后仍然没有可用文本的页面。

当前实现的输出包括 UTF-8 Markdown、结构化 JSON、页面文本、页码、解析引擎、分类状态和 OCR 路由结果。Markdown 和 JSON 保存到项目 documents 目录，结果同时写入 SQLite。应用刷新后可以按照 Asset 标识恢复文档预览，不需要重新解析原始 PDF。

开源组件的职责划分如下。

| 组件 | 项目地址 | 适合职责 | 当前选择 |
| --- | --- | --- | --- |
| pdf-inspector | https://github.com/firecrawl/pdf-inspector | 快速判断文字型、扫描型、图片型和混合型 PDF，并提供页级 OCR 路由 | 作为后续分类器候选。Python 绑定当前需要 Rust 和 Maturin 从源码构建，Windows 普通用户分发前不作为硬依赖 |
| PyMuPDF | https://github.com/pymupdf/PyMuPDF | 文本层提取、页面渲染、坐标和基础表格检测 | 当前数字 PDF 提取器和页面渲染器 |
| RapidOCR | https://github.com/RapidAI/RapidOCR | 本地中文和英文 OCR，使用 ONNX Runtime 执行 | 当前扫描页 OCR 引擎 |
| Docling | https://github.com/docling-project/docling | 复杂版面、阅读顺序、表格、公式、图片和多种办公文档 | 后续复杂文档 Worker，不放入基础界面的同步请求 |
| MarkItDown | https://github.com/microsoft/markitdown | docx, pptx, xlsx, html, txt, md 和 PDF 的轻量 Markdown 转换 | 后续 Word、PPTX、HTML 和 Markdown 的快速文本通道 |

pdf-inspector 的分类能力适合放到统一 DocumentRouter 后面。桌面版可以在 Rust 主进程中调用它，也可以构建独立 sidecar。无论以后替换分类器还是增加 Docling，前端继续只读取 DocumentParseResult，避免界面直接耦合具体解析库。Docling 负责需要页面结构和表格准确性的任务，MarkItDown 负责只需要搜索和对话上下文的轻量任务。这样可以同时控制安装体积、解析速度和结果质量。

PDF 解析产物包括以下内容。

- 文档级元数据。
- 页级文本和坐标。
- 标题层级和段落。
- 表格结构和单元格。
- 图片和图片说明。
- OCR 置信度。
- Markdown 表示。
- 结构化 JSON 表示。
- 原文页码引用。

从 PDF 提取的表格先创建 TableCandidate，不直接成为训练数据集。用户需要在预览中确认表头、跨页合并、空单元格和字段类型，确认后才生成 DatasetVersion。

扫描 PDF 的 OCR 是可选高成本步骤。界面需要显示预计页数、执行设备和任务进度。解析失败时保留已经成功的页级结果，并输出 DocumentParseError 和失败页码。

## 数据集和机器学习流程

机器学习第一版聚焦结构化表格分类和回归，不在首版同时实现时间序列、图像训练、文本微调和大型深度学习训练。

标准流程如下。

1. 选择 DatasetVersion。
2. 选择目标列。
3. 判断分类或回归任务。
4. 检查字段类型、空值、常量列、重复列和疑似标识列。
5. 配置训练集、验证集和测试集划分。
6. 配置数值、类别、日期和文本字段处理。
7. 选择候选算法和评价指标。
8. 运行训练任务。
9. 保存预处理流水线、模型、指标、参数、随机种子和依赖版本。
10. 展示结果并允许生成预测文件。

需要显式提示但不自动隐藏处理的风险包括目标泄漏、类别不平衡、时间顺序破坏、样本量过小、目标列缺失和训练测试重复。用户确认后的配置保存为 TrainingSpec。

传统模型优先包含 Logistic Regression, Random Forest, HistGradientBoosting 和适用的线性回归模型。PyTorch 第一阶段用于后续扩展和可选神经网络模型，不应成为普通表格任务的强制依赖路径。

## OpenClaw 对话窗口设计

OpenClaw 是可选对话和任务编排连接器，不是项目数据和任务状态的唯一来源。即使 OpenClaw 未安装或连接失败，文件导入、解析、训练和导出仍然必须可用。

桌面端连接本机 OpenClaw Gateway，并把流式消息转换为统一 ChatEvent。GUI 不直接依赖 Gateway 原始消息格式，OpenClawConnector 负责连接、认证、重连、会话和消息转换。

允许提供给 OpenClaw 的应用工具包括以下内容。

- project_get_summary
- asset_list
- dataset_get_profile
- document_search
- training_create_plan
- job_get_status
- model_get_metrics
- artifact_create_export_request

OpenClaw 不获得通用文件系统、任意路径读取、任意 Shell 或数据库连接权限。工具参数使用 project_id, asset_id, dataset_version_id 和 model_run_id，不接受未经限制的绝对路径。

只读查询可以直接执行。创建数据集版本、启动训练、覆盖导出文件、上传云端和调用付费模型必须先生成计划，并进入 waiting_confirmation 状态。用户确认后由应用任务服务执行，不由聊天界面绕过任务系统。

发送给模型的上下文需要显示来源范围。默认只发送用户当前选择的资产摘要、字段定义、统计结果和必要片段。原始完整表格、完整 PDF 和敏感字段只有在用户明确允许后才能发送到外部模型。

## 本地和云端切换

Workspace Client Contract 对界面提供相同方法，底层实现分为 LocalWorkspaceClient 和 RemoteWorkspaceClient。

LocalWorkspaceClient 连接本机 Python Task Service，文件保存在本地项目目录，凭据保存在操作系统安全存储中。RemoteWorkspaceClient 连接云端 API，文件保存在对象存储，元数据保存在关系数据库，训练任务进入云端队列。

云端迁移需要增加以下能力。

- 用户和组织账号。
- 项目权限和成员角色。
- 分片上传、断点续传和内容哈希去重。
- 对象存储和生命周期管理。
- Worker 容器和资源配额。
- 每用户或每租户隔离的 OpenClaw 运行边界。
- API 限流、任务计费和用量记录。
- 审计日志和数据删除流程。

本地版不提前实现全部云端设施，但 Project, Asset, Job, Artifact 和 ToolDefinition 的标识格式从第一版开始保持可迁移。

## 错误类型和错误信息

公开边界使用稳定错误类型，内部实现不滥用异常包装。第一阶段错误类型如下。

- FileAccessError: 文件不存在、权限不足或文件被占用。
- UnsupportedFileFormatError: 文件格式不受支持或扩展名与签名冲突。
- FileEncodingError: 文本编码无法可靠识别或解码失败。
- ArchiveExtractionError: 解压失败、路径非法或资源限制触发。
- SpreadsheetParseError: 工作簿、Sheet 或单元格解析失败。
- DocumentParseError: PDF、OCR 或文档结构解析失败。
- DatasetSchemaError: 字段、类型或表头配置无效。
- TrainingConfigurationError: 目标列、数据划分或参数无效。
- ComputeDeviceError: CPU、CUDA、显卡架构或显存不满足要求。
- ModelTrainingError: 模型拟合、评估或保存失败。
- ExportError: 输出路径、编码或格式写入失败。
- OpenClawConnectionError: Gateway 连接、认证或协议失败。
- PermissionDeniedError: 用户未批准需要确认的操作。
- InternalTaskError: 未归类的任务内部错误。

错误响应至少包含 error_type, message, operation, recoverable 和 details。界面显示简洁中文信息，详细技术信息保存在任务详情和日志中。错误信息禁止只写 failed, unknown error 或解析失败等无法定位问题的内容。

## 中文说明和英文 comment 规范

本 README 使用中文详细说明业务流程、边界条件、数据结构和实现原因。后续源代码中的 comment 使用英文，便于工具链、静态检查和跨语言协作。

英文 comment 只用于解释以下内容。

- 不直观的算法选择。
- 第三方库限制。
- 安全边界。
- 性能优化原因。
- 平台差异。
- 无法通过类型和函数名称表达的约束。

禁止使用逐行翻译代码行为的无效 comment。公开 API、配置项和错误类型需要中文文档说明，源代码实现位置保留简洁英文 comment。

## 测试要求

测试分为单元测试、契约测试、集成测试、GUI 测试和打包测试。

- 单元测试覆盖编码判断、文件签名、解压路径、字段推断和指标计算。
- 契约测试确保 LocalWorkspaceClient 和 RemoteWorkspaceClient 返回相同结构。
- 集成测试覆盖导入、解压、解析、数据集生成、训练和导出闭环。
- GUI 测试覆盖面板调整、长文件名、中文文本、高 DPI、加载状态和错误状态。
- 打包测试在未安装 Python、Node.js 和开发工具的 Windows 环境中启动安装包。
- 大文件测试覆盖多 Sheet XLSX、大型 CSV、扫描 PDF 和嵌套压缩包。
- 乱码测试覆盖 UTF-8, UTF-8 BOM, UTF-16, GB18030 和 ZIP 中文文件名。
- GPU 测试记录 PyTorch、CUDA、驱动、设备名称和计算架构。

## Windows 打包和发布

第一版以 Windows x64 为主要目标。React 前端构建后嵌入 Tauri，Python Task Service 使用 PyInstaller 单文件模式打包为 sidecar，由 Tauri 主进程负责启动、等待就绪和退出回收。普通用户不需要另外安装 Python、Node.js、Rust、RapidOCR 或 ONNX Runtime。

安装包需要包含以下内容。

- Tauri 桌面应用。
- Python sidecar。
- 必要的解析和机器学习依赖。
- 默认配置和数据库迁移文件。
- 第三方许可证和 NOTICE 文件。
- 卸载程序。

当前基础安装包内置 RapidOCR 的检测、方向分类和中文英文识别三个 ONNX 模型，保证扫描 PDF 在离线环境可用。PyInstaller 构建结束后会运行 sidecar 的 check-resources 模式，确认模型能够从打包资源加载。当前 sidecar 大约 170 MB，NSIS 安装包大约 173 MB。后续大型 Docling 模型、机器学习模型权重和 CUDA 依赖仍作为可选组件，不无条件放入基础安装包。

Tauri 使用固定回环地址 127.0.0.1 和端口 8765 连接 sidecar。桌面窗口创建前最多等待 15 秒，服务未就绪时返回 SidecarReadyTimeoutError。配置错误返回 SidecarConfigurationError，进程启动失败返回 SidecarStartError。关闭桌面窗口时，Windows 使用无窗口的 taskkill 进程树回收方式，同时终止 PyInstaller 外层进程和内部服务进程，避免残留端口和后台进程。

正式分发需要 Windows 代码签名、版本号、安装日志、崩溃日志导出和升级策略。便携版可以用于内部测试，面向普通用户优先提供安装程序。

## 当前原型运行方式

开发工具需要 Node.js, pnpm 10, Rust stable 和 Python 3.11。当前机器默认使用 D:\Python\python11，也可以通过 ML_GUI_PYTHON 指定其他 Python 3.11 路径。首次运行前在仓库根目录执行 pnpm install，并在 services\task-service 目录安装 pyproject.toml 中声明的 Python 依赖。

启动本地任务服务。

```powershell
Set-Location services\task-service
D:\Python\python11\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8765
```

启动本地 Web 工作台。

```powershell
Set-Location F:\CodeX
pnpm dev
```

启动桌面开发窗口。

```powershell
Set-Location F:\CodeX
pnpm desktop:dev
```

desktop:dev 会先创建 .runtime\sidecar-venv 专用打包环境，生成带目标三元组的 sidecar，再启动 Tauri。该虚拟环境、PyInstaller 中间文件和生成的 sidecar 均被 Git 忽略。网络需要自定义 Python 镜像时可以设置 ML_GUI_PIP_INDEX_URL，不在项目脚本中关闭 TLS 证书校验。

生成 Windows NSIS 安装包。

```powershell
Set-Location F:\CodeX
pnpm desktop:build
```

生成不带安装器的便携测试目录。

```powershell
Set-Location F:\CodeX
pnpm desktop:build:portable
```

构建入口 scripts\build_windows_sidecar.ps1 会验证 Python 3.11、安装 packaging 可选依赖、调用 PyInstaller，并把 task-service-x86_64-pc-windows-msvc.exe 写入 Tauri binaries 目录。Tauri 根据 externalBin 配置把它复制为发布目录中的 task-service.exe，并嵌入 NSIS 安装包。

构建产物如下。

- 桌面主程序: apps\desktop\src-tauri\target\release\machinglearing-gui.exe。
- 发布 sidecar: apps\desktop\src-tauri\target\release\task-service.exe。
- NSIS 安装包: apps\desktop\src-tauri\target\release\bundle\nsis\MachingLearing GUI_0.1.0_x64-setup.exe。

便携测试必须同时保留主程序和 task-service.exe，不能只复制主程序。面向用户分发时使用 NSIS 安装包。当前安装模式为 currentUser，不需要管理员权限。正式公开发布前仍需完成 Windows 代码签名、第三方许可证汇总和升级签名配置。

默认情况下 WebView 数据保存在当前用户的应用数据目录。受限环境或便携测试可以在启动前设置 ML_GUI_WEBVIEW_DATA_DIR，将缓存和本地存储写入指定的可写目录。

## 当前文件导入能力

工作台已经接入真实的本地文件导入接口。左侧栏的导入按钮支持 csv, xlsx, pdf, zip, tar, tgz 和 gz。浏览器以原始二进制请求体上传文件，文件名通过 UTF-8 URL 编码请求头传递，不依赖 multipart 对中文文件名进行二次转换。

导入普通 CSV 或 XLSX 时，服务会把原始文件保存到项目 source 目录，计算 SHA-256，写入 assets 元数据表，并返回最多 100 行的数据预览。CSV 按 BOM、严格 UTF-8、GB18030 和编码检测结果的顺序识别编码。XLSX 当前读取第一个工作表，保留数值、布尔值和日期等单元格类型。

导入压缩文件时，服务会创建独立的 extracted 子目录，解压后为每个普通文件创建子资产，并自动预览找到的第一个 CSV 或 XLSX。ZIP 和 TAR 解压会拒绝路径穿越、符号链接、非普通文件、超过 2000 个文件或解压后总计超过 512 MB 的内容。原始压缩文件和解压资产通过 parentAssetId 保持来源关系。

当前版本已经实现表格预览持久化。刷新应用后，前端会从 SQLite 读取最新可预览资产并恢复表格。右侧字段确认区允许把每个字段设为 text, integer, number 或 boolean。确认后生成不可变的 DatasetVersion，并在项目 datasets 目录写入使用 Zstandard 压缩的 Parquet 文件。同一源资产再次确认会生成递增版本，不覆盖之前的数据集文件。

Parquet 下载接口按数据集版本返回对应文件。字段转换失败时返回 DatasetSchemaError，错误详情包含行号、字段名、目标类型和原始值，不会静默把无效数值改为空值。

PDF 导入会自动区分数字 PDF、扫描 PDF 和混合 PDF。数字页使用 PyMuPDF 直接提取，扫描页使用 RapidOCR 本地识别，混合 PDF 只对缺少文本层的页面执行 OCR。解析结果保存为 UTF-8 Markdown 和 JSON，并可以在刷新后恢复到中间预览区。OCR 运行完全在本机完成，当前流程不上传原始文档到外部服务。

## 案例文件和完整测试

可直接从 GUI 导入的案例文件位于 services/task-service/tests/fixtures。

- chinese_sales_utf8.csv: UTF-8 中文表格，用于字段类型确认和 Parquet 版本导出。
- chinese_sales.xlsx: 中文 Sheet 和布尔字段，用于 XLSX 预览。
- chinese_archive.zip: 包含 GB18030 中文 CSV 和中文路径，用于解压、父子资产和乱码测试。
- digital_chinese_report.pdf: 包含可提取中文文本层的数字 PDF。
- scanned_chinese_report.pdf: 只有中文图像的扫描 PDF，用于 RapidOCR 测试。
- mixed_chinese_report.pdf: 第一页为文字层，第二页为扫描图像，用于按页 OCR 路由测试。

二进制案例由 tests/build_pdf_fixtures.py 可重复生成。该脚本只生成测试数据，不写入用户项目目录。完整后端测试覆盖项目持久化、中文文件名、UTF-8、GB18030、XLSX、压缩包安全边界、表格预览恢复、字段确认、递增数据集版本、Parquet 下载、数字 PDF、扫描 PDF 和混合 PDF。

算法专用测试数据位于 `services/task-service/tests/fixtures/algorithms`。这些 CSV 由 `tests/build_algorithm_fixtures.py` 使用固定随机种子生成，采用 UTF-8 without BOM，并在 `fixture_manifest.json` 中记录行数、任务类型、许可证、生成方式和 SHA-256。测试目录包含分类、回归、聚类、单因素方差分析、多因素方差分析以及同时支持序列回归和序列分类的时间序列数据。数据包含中文类别和分组值，用于同时检查算法流程与编码处理。

算法 fixture 是本项目生成的确定性合成测试数据，使用 CC0-1.0。它们用于自动化测试和错误定位，不冒充真实业务数据。重新生成后必须执行清单测试；如果随机逻辑或文件内容发生变化，新的哈希必须与代码变更一起审核。

```powershell
Set-Location F:\CodeX\services\task-service
F:\CodeX\.runtime\sidecar-venv\Scripts\python.exe tests\build_pdf_fixtures.py
F:\CodeX\.runtime\sidecar-venv\Scripts\python.exe tests\build_algorithm_fixtures.py
F:\CodeX\.runtime\sidecar-venv\Scripts\python.exe -m pytest -q
```

## Git 开发规则

每个可验证步骤完成后执行一次提交并推送到以下仓库。

https://github.com/zzz-sudo/MachingLearing-GUI.git

提交应保持单一目的，例如项目骨架、文件导入、XLSX 解析、PDF 解析、模型训练、OpenClaw 连接、GUI 调整和打包配置分别提交。提交前需要执行格式检查、相关测试和 git diff 检查。

不得在提交中加入临时数据、真实用户文件、模型密钥、OpenClaw 凭据、构建缓存和大型模型权重。第三方代码必须记录来源、许可证和修改范围。

## 实施阶段

### 阶段一: 工作台基础

建立 React, TypeScript, Tauri 和 Python Task Service 骨架，实现项目创建、项目打开、统一任务状态、日志和基础三栏布局。

### 阶段二: 文件和数据

实现文件导入、压缩文件解压、编码确认、CSV 和 XLSX 解析、数据预览、字段定义和 Parquet 数据集版本。

### 阶段三: PDF 和文档

接入 Docling，完成 PDF 文本、页面、表格、OCR、Markdown、JSON 和 TableCandidate 预览确认。

### 阶段四: 机器学习闭环

完成分类和回归配置、预处理、训练、评估、模型保存、批量预测和结果导出。

### 阶段五: OpenClaw

实现 OpenClawConnector、对话 Dock、只读工具、计划确认和受控任务调用。先保证只读和计划流程稳定，再开放训练和外部服务调用。

### 阶段六: Web 和云端准备

验证浏览器运行方式，完成 Workspace Client Contract 双实现，并设计账号、上传、对象存储、任务队列和租户隔离。

### 阶段七: 发布

完成 Windows 安装程序、代码签名、升级、许可证清单、无开发环境启动测试和高 DPI GUI 检查。

## 第一版验收闭环

第一版以一个明确流程作为验收目标。

1. 用户创建项目。
2. 用户导入包含中文字段的 XLSX 或 ZIP。
3. 应用正确解压并显示无乱码文件名。
4. 用户选择 Sheet、表头和目标列。
5. 应用生成数据剖析结果和 DatasetVersion。
6. 用户配置分类或回归任务。
7. 应用在本地 Worker 中训练并显示进度。
8. 应用展示指标、参数和模型文件。
9. 用户通过 OpenClaw 询问结果解释。
10. OpenClaw 使用受控工具读取指标，不直接访问任意文件。
11. 用户导出预测 XLSX，中文字段和内容保持正确编码。
12. 关闭并重新打开应用后，项目、任务、模型和结果仍可恢复。

## Windows 签名、版本和升级发布

正式发布分成两种彼此独立的签名。Windows Authenticode 使用受信任代码签名证书为主程序、sidecar 和 NSIS 安装程序签名，用于证明发布者身份并降低 Windows SmartScreen 的未知发布者提示。Tauri Updater 使用独立的 minisign 密钥为更新产物签名，用于防止更新文件在下载或托管过程中被替换。两类密钥用途不同，不能相互替代。

仓库只保存 Tauri Updater 公钥，路径为 `apps/desktop/src-tauri/tauri.release.conf.json`。本机生成的更新私钥位于 `.runtime/updater.key`，该目录已被 Git 忽略，不得提交、打印到日志或放入安装包。首次配置 GitHub 发布环境时，需要把该文件完整内容写入仓库 Secret `TAURI_SIGNING_PRIVATE_KEY`。当前密钥没有密码，因此 `TAURI_SIGNING_PRIVATE_KEY_PASSWORD` 可以为空；正式生产发布前建议重新生成带密码的密钥，同时替换配置中的公钥，并把密码写入同名 GitHub Secret。已经发布更新后不能随意更换更新公钥，否则旧版本客户端无法验证新更新。

Windows 代码签名需要配置以下 GitHub Secrets。

- `WINDOWS_CERTIFICATE_BASE64`: PFX 证书文件的 Base64 内容，不是证书路径。
- `WINDOWS_CERTIFICATE_PASSWORD`: PFX 导出密码。
- `TAURI_SIGNING_PRIVATE_KEY`: Tauri Updater 私钥完整内容。
- `TAURI_SIGNING_PRIVATE_KEY_PASSWORD`: 更新私钥密码，无密码密钥可留空。

正式构建通过 `scripts/sign_windows.ps1` 临时解码 PFX，调用 Windows SDK 的 `signtool.exe` 使用 SHA-256 和 RFC 3161 时间戳完成签名，然后在 `finally` 中删除临时证书。Tauri 的 `signCommand` 会依次覆盖 Python sidecar、主程序和安装程序。缺少证书、密码、待签名文件或 Signing Tools 时，脚本会输出明确的 `WindowsCertificateMissingError`、`WindowsCertificatePasswordMissingError`、`WindowsSigningTargetMissingError` 或 `WindowsSignToolMissingError`。普通 `pnpm desktop:build` 不要求证书，只有 `pnpm release:build` 和标签发布使用正式签名配置。

### 统一版本管理

版本号必须使用 SemVer 格式，并在根工作区、Web、桌面 npm 包、共享契约、Python 服务、Cargo 包和 Tauri 配置中完全一致。不要逐个手工修改这些文件。升级版本时执行以下命令。

```powershell
pnpm release:version -- 0.2.0
pnpm release:check
```

`scripts/release_version.py` 使用结构化 JSON 读取和受 TOML section 限定的版本字段替换。版本不一致时返回 `VersionMismatchError`，版本格式错误时返回 `InvalidSemanticVersionError`，Git 标签与项目版本不一致时返回 `ReleaseTagMismatchError`。完成版本变更、测试和审核后创建与版本一致的标签，例如 `v0.2.0`。推送标签会触发 `.github/workflows/release-windows.yml`，构建 sidecar、生成许可证清单、执行两类签名、发布 NSIS 安装包、更新签名和 `latest.json`。

桌面界面左下角的设置按钮打开版本升级窗口。客户端从 GitHub Release 的 `latest.json` 检查版本，发现新版本后下载并验证 Tauri 更新签名，以被动模式运行 NSIS 更新，然后重启应用。Web 预览只显示当前运行形态，不执行桌面安装操作。正式环境只使用 HTTPS 更新端点。

### 安装包许可证清单

`scripts/generate_third_party_licenses.py` 从三个真实构建来源生成许可证清单，而不是维护一份容易过期的手工表格。

- Node 依赖来自 `pnpm licenses list --prod --json`。
- Python 依赖来自 sidecar 隔离环境的 `pip inspect`，并沿 Task Service 运行时依赖关系收集。
- Rust 依赖来自锁定的 `Cargo.lock` 和 `cargo metadata --locked`。

生成文件为 `apps/desktop/src-tauri/resources/licenses/THIRD_PARTY_LICENSES.json` 和 `THIRD_PARTY_NOTICES.txt`，构建时作为 Tauri resource 放入安装目录。JSON 文件用于自动审计，TXT 文件用于安装后人工查看。执行顺序如下。

```powershell
pnpm desktop:sidecar
pnpm release:licenses
```

当前 PDF 解析依赖 PyMuPDF。其许可证元数据明确为 GNU AGPL 3.0 或 Artifex 商业许可证，因此生成器会把它列入 `manualReview`。在公开分发 Windows 安装包前，必须选择并落实 AGPL 整体合规方案，或者取得 Artifex 商业许可证。许可证清单本身不能替代这个决定。任何 `UNKNOWN` 许可证也会阻止把清单视为已经完成法律审核。

### 发布验证顺序

1. 执行版本同步和 `pnpm release:check`。
2. 执行 `pnpm install --frozen-lockfile`、`pnpm typecheck` 和 `pnpm test`。
3. 构建 sidecar 并执行 `pnpm release:licenses`，检查 `manualReview`。
4. 在有 PFX、更新私钥和 Windows SDK 的隔离环境执行 `pnpm release:build`。
5. 使用 `Get-AuthenticodeSignature` 检查主程序、sidecar 和安装程序的签名状态与发布者。
6. 在没有开发环境的 Windows 用户账户执行安装、启动、更新、重启和卸载测试。
7. 推送与版本一致的 Git 标签，确认 GitHub Release 同时包含安装程序、更新签名和 `latest.json`。
