项目输入文件格式:
CSV、XLSX、PDF、MD、TXT、JSON、ZIP、TAR、TGZ、GZ。测试数据使用 UTF-8 文本和项目内公开夹具，压缩包只用于解压安全流程验证。
项目输出文件类型:
Parquet 数据集、Markdown、JSON、TXT、DOCX、XLSX、模型文件、图形规格 JSON、PNG、SVG、HTML 和任务审计记录。
项目功能:
提供本地算法、数据解析、图形生成和结果追溯的可重复测试工作区。
作者: Kuroneko

# 默认测试工作区

这个目录是真实文件夹，不是内存中的虚拟目录。桌面程序和网页程序默认打开这里，便于检查文件树、数据集版本、算法任务和图形规格。

目录约定:

- `source` 保存原始输入和可重复测试数据。
- `datasets` 保存确认字段后的 Parquet 数据集。
- `models` 保存模型产物。
- `predictions` 保存预测结果。
- `charts` 保存图形规格和后续导出图形。
- `reports` 保存分析报告。
- `logs` 保存任务日志。
- `temp` 保存临时文件，不作为最终产物。

`services/task-service/tests/fixtures` 是自动化测试的标准夹具目录。这里的 `source` 文件用于手动打开、导入和演示，两者保持相同来源和哈希校验。
