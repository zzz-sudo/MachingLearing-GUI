# MachingLearing GUI

作者: Kuroneko

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

PDF 主解析器规划使用 Docling，用于页面布局、阅读顺序、表格、公式、图片和 OCR。MarkItDown 可以作为生成 LLM 文本上下文的轻量转换器，但不能替代页面坐标和结构化表格结果。

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

第一版以 Windows x64 为主要目标。React 前端构建后嵌入 Tauri，Python Task Service 和必要 Worker 使用 PyInstaller 或等效工具打包为 sidecar。

安装包需要包含以下内容。

- Tauri 桌面应用。
- Python sidecar。
- 必要的解析和机器学习依赖。
- 默认配置和数据库迁移文件。
- 第三方许可证和 NOTICE 文件。
- 卸载程序。

模型权重、OCR 权重和大型 CUDA 依赖不应全部无条件塞入基础安装包。需要划分基础组件和可选运行组件，并在设置中显示下载大小、版本和安装位置。

正式分发需要 Windows 代码签名、版本号、安装日志、崩溃日志导出和升级策略。便携版可以用于内部测试，面向普通用户优先提供安装程序。

## 当前原型运行方式

开发工具需要 Node.js, pnpm 10, Rust stable 和 D:\Python\python11。首次运行前在仓库根目录执行 pnpm install，并在 services\task-service 目录安装 pyproject.toml 中声明的 Python 依赖。

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

生成不带安装器的 Windows exe。

```powershell
Set-Location F:\CodeX
pnpm desktop:build
```

构建后的 exe 位于 apps\desktop\src-tauri\target\release。当前 exe 复用本机运行的 Python Task Service，后续发布阶段再把 Python 服务打包为 sidecar，并由桌面主进程统一启动和关闭。

默认情况下 WebView 数据保存在当前用户的应用数据目录。受限环境或便携测试可以在启动前设置 ML_GUI_WEBVIEW_DATA_DIR，将缓存和本地存储写入指定的可写目录。

## 当前文件导入能力

工作台已经接入真实的本地文件导入接口。左侧栏的导入按钮支持 csv, xlsx, zip, tar, tgz 和 gz。浏览器以原始二进制请求体上传文件，文件名通过 UTF-8 URL 编码请求头传递，不依赖 multipart 对中文文件名进行二次转换。

导入普通 CSV 或 XLSX 时，服务会把原始文件保存到项目 source 目录，计算 SHA-256，写入 assets 元数据表，并返回最多 100 行的数据预览。CSV 按 BOM、严格 UTF-8、GB18030 和编码检测结果的顺序识别编码。XLSX 当前读取第一个工作表，保留数值、布尔值和日期等单元格类型。

导入压缩文件时，服务会创建独立的 extracted 子目录，解压后为每个普通文件创建子资产，并自动预览找到的第一个 CSV 或 XLSX。ZIP 和 TAR 解压会拒绝路径穿越、符号链接、非普通文件、超过 2000 个文件或解压后总计超过 512 MB 的内容。原始压缩文件和解压资产通过 parentAssetId 保持来源关系。

当前预览结果只保存在本次界面会话中。刷新应用后仍会显示已导入资产，但不会自动恢复上次表格预览；数据集版本持久化和已导入资产重新预览将在下一阶段实现。

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
