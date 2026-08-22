from __future__ import annotations

from app.models import AlgorithmCatalog, AlgorithmDefinition, AlgorithmParameter


def integer_parameter(
    parameter_id: str,
    label: str,
    default: int,
    minimum: int,
    maximum: int,
    description: str,
    step: int = 1,
) -> AlgorithmParameter:
    return AlgorithmParameter(
        id=parameter_id,
        label=label,
        value_type="integer",
        default=default,
        minimum=minimum,
        maximum=maximum,
        step=step,
        description=description,
    )


def number_parameter(
    parameter_id: str,
    label: str,
    default: float,
    minimum: float,
    maximum: float,
    description: str,
    step: float,
) -> AlgorithmParameter:
    return AlgorithmParameter(
        id=parameter_id,
        label=label,
        value_type="number",
        default=default,
        minimum=minimum,
        maximum=maximum,
        step=step,
        description=description,
    )


TREE_PARAMETERS = [
    integer_parameter("n_estimators", "树数量", 200, 10, 2000, "参与集成的决策树数量", 10),
    integer_parameter("max_depth", "最大深度", 8, 1, 64, "单棵树允许的最大深度"),
]

XGBOOST_PARAMETERS = [
    integer_parameter("n_estimators", "迭代轮数", 300, 10, 3000, "梯度提升迭代轮数", 10),
    integer_parameter("max_depth", "最大深度", 6, 1, 32, "单棵树允许的最大深度"),
    number_parameter("learning_rate", "学习率", 0.05, 0.001, 1.0, "每轮提升的步长", 0.001),
    number_parameter("subsample", "样本比例", 0.8, 0.1, 1.0, "每轮使用的训练样本比例", 0.05),
]

CLUSTER_COUNT = [
    integer_parameter("n_clusters", "聚类数量", 3, 2, 100, "期望划分的聚类数量"),
]

DENSITY_PARAMETERS = [
    number_parameter("eps", "邻域半径", 0.5, 0.01, 20.0, "密度邻域的最大距离", 0.01),
    integer_parameter("min_samples", "最小样本数", 5, 2, 500, "形成核心点所需的邻域样本数"),
]

SEQUENCE_PARAMETERS = [
    integer_parameter("window_size", "窗口长度", 12, 2, 512, "每个训练样本包含的连续时间步数量"),
    integer_parameter("horizon", "预测步长", 1, 1, 128, "从窗口末端向后预测的时间步距离"),
    integer_parameter("hidden_size", "隐藏维度", 32, 4, 1024, "循环网络隐藏状态的维度", 4),
    integer_parameter("num_layers", "网络层数", 1, 1, 8, "循环网络堆叠层数"),
    integer_parameter("epochs", "训练轮数", 30, 1, 1000, "完整遍历训练集的次数"),
    integer_parameter("batch_size", "批大小", 32, 1, 4096, "每次参数更新使用的样本数量"),
    number_parameter("learning_rate", "学习率", 0.001, 0.000001, 1.0, "优化器更新参数的步长", 0.0001),
]

REGULARIZATION_PARAMETERS = [
    number_parameter("alpha", "正则强度", 1.0, 0.000001, 10000.0, "正则化强度", 0.1),
]

ELASTIC_NET_PARAMETERS = [
    number_parameter("alpha", "正则强度", 1.0, 0.000001, 10000.0, "正则化强度", 0.1),
    number_parameter("l1_ratio", "L1 比例", 0.5, 0.0, 1.0, "L1 与 L2 正则化的混合比例", 0.05),
]

HUBER_PARAMETERS = [
    number_parameter("epsilon", "稳健阈值", 1.35, 1.01, 10.0, "残差进入线性损失的阈值", 0.05),
]

QUANTILE_PARAMETERS = [
    number_parameter("quantile", "目标分位数", 0.5, 0.01, 0.99, "需要估计的条件分位数", 0.01),
    number_parameter("alpha", "正则强度", 1.0, 0.0, 10000.0, "正则化强度", 0.1),
]

TEST_PARAMETERS = [
    number_parameter("population_mean", "总体均值", 0.0, -1_000_000.0, 1_000_000.0, "单样本检验的理论均值", 0.1),
]


def _definition(
    algorithm_id: str,
    name: str,
    task_type: str,
    family: str,
    description: str,
    *,
    requires_target: bool = False,
    requires_factors: bool = False,
    requires_time: bool = False,
    supports_gpu: bool = False,
    status: str = "available",
    dependencies: list[str] | None = None,
    chart_templates: list[str] | None = None,
    parameters: list[AlgorithmParameter] | None = None,
) -> AlgorithmDefinition:
    return AlgorithmDefinition(
        id=algorithm_id,
        name=name,
        task_type=task_type,
        family=family,
        description=description,
        requires_target=requires_target,
        requires_factors=requires_factors,
        requires_time=requires_time,
        supports_gpu=supports_gpu,
        status=status,
        dependencies=dependencies or [],
        chart_templates=chart_templates or [],
        parameters=parameters or [],
    )


# This catalog is the single source of truth shared by validation and the UI.
ALGORITHMS = [
    _definition("logistic_regression", "逻辑回归", "classification", "线性模型", "分类任务的可解释基线", requires_target=True),
    _definition("decision_tree_classifier", "决策树分类", "classification", "树模型", "使用单棵决策树完成分类", requires_target=True, parameters=[TREE_PARAMETERS[1]]),
    _definition("random_forest_classifier", "随机森林分类", "classification", "集成学习", "通过多棵随机决策树完成稳健分类", requires_target=True, dependencies=["scikit-learn"], chart_templates=["confusion_matrix", "feature_importance"], parameters=TREE_PARAMETERS),
    _definition("extra_trees_classifier", "极端随机树分类", "classification", "集成学习", "通过更强的随机划分降低模型方差", requires_target=True, parameters=TREE_PARAMETERS),
    _definition("hist_gradient_boosting_classifier", "直方图梯度提升分类", "classification", "集成学习", "适合中大型表格数据的梯度提升分类", requires_target=True),
    _definition("xgboost_classifier", "XGBoost 分类", "classification", "梯度提升", "支持早停和 GPU 的梯度提升分类", requires_target=True, supports_gpu=True, dependencies=["xgboost"], chart_templates=["confusion_matrix", "feature_importance"], parameters=XGBOOST_PARAMETERS),
    _definition("linear_regression", "线性回归", "regression", "线性模型", "连续目标预测的可解释基线", requires_target=True),
    _definition("ridge_regression", "岭回归", "regression", "线性模型", "使用 L2 正则化的线性回归", requires_target=True, parameters=[number_parameter("alpha", "正则强度", 1.0, 0.000001, 10000.0, "L2 正则化强度", 0.1)]),
    _definition("random_forest_regressor", "随机森林回归", "regression", "集成学习", "通过多棵随机决策树预测连续目标", requires_target=True, dependencies=["scikit-learn"], chart_templates=["scatter", "residual", "feature_importance"], parameters=TREE_PARAMETERS),
    _definition("extra_trees_regressor", "极端随机树回归", "regression", "集成学习", "通过更强随机性完成连续目标预测", requires_target=True, parameters=TREE_PARAMETERS),
    _definition("hist_gradient_boosting_regressor", "直方图梯度提升回归", "regression", "集成学习", "适合中大型表格数据的梯度提升回归", requires_target=True),
    _definition("xgboost_regressor", "XGBoost 回归", "regression", "梯度提升", "支持早停和 GPU 的梯度提升回归", requires_target=True, supports_gpu=True, dependencies=["xgboost"], chart_templates=["scatter", "residual", "feature_importance"], parameters=XGBOOST_PARAMETERS),
    _definition("kmeans", "K-Means", "clustering", "质心聚类", "按照样本到质心的距离划分聚类", dependencies=["scikit-learn"], chart_templates=["cluster_scatter", "heatmap"], parameters=CLUSTER_COUNT),
    _definition("mini_batch_kmeans", "MiniBatch K-Means", "clustering", "质心聚类", "使用小批次处理较大的数据集", parameters=CLUSTER_COUNT),
    _definition("agglomerative", "层次聚类", "clustering", "层次聚类", "自底向上合并相近的样本簇", parameters=CLUSTER_COUNT),
    _definition("dbscan", "DBSCAN", "clustering", "密度聚类", "发现任意形状聚类并标识噪声点", parameters=DENSITY_PARAMETERS),
    _definition("hdbscan", "HDBSCAN", "clustering", "密度聚类", "从不同密度层次提取稳定聚类", parameters=[integer_parameter("min_cluster_size", "最小聚类大小", 5, 2, 1000, "被识别为独立聚类所需的最少样本数")]),
    _definition("gaussian_mixture", "高斯混合模型", "clustering", "概率聚类", "使用高斯分布混合表示样本群体", parameters=[integer_parameter("n_components", "分量数量", 3, 2, 100, "高斯分布分量数量")]),
    _definition("birch", "BIRCH", "clustering", "层次聚类", "面向大型数据的增量层次聚类", parameters=CLUSTER_COUNT),
    _definition("one_way_anova", "单因素方差分析", "anova", "统计分析", "检验一个分类因素对连续因变量的影响", requires_target=True, requires_factors=True, dependencies=["statsmodels", "scipy"], chart_templates=["anova_effect", "boxplot"]),
    _definition("factorial_anova", "多因素方差分析", "anova", "统计分析", "检验多个分类因素的主效应和交互效应", requires_target=True, requires_factors=True, parameters=[AlgorithmParameter(id="sum_squares_type", label="平方和类型", value_type="select", default="2", options=["1", "2", "3"], description="不平衡设计通常使用 Type II，含完整交互解释时可使用 Type III"), AlgorithmParameter(id="include_interactions", label="包含交互项", value_type="boolean", default=True, description="是否在模型中加入因素之间的交互项")]),
    _definition("rnn_regressor", "RNN 序列回归", "sequence_regression", "循环神经网络", "使用普通循环单元预测连续序列目标", requires_target=True, requires_time=True, supports_gpu=True, parameters=SEQUENCE_PARAMETERS),
    _definition("lstm_regressor", "LSTM 序列回归", "sequence_regression", "循环神经网络", "使用长短期记忆单元预测连续序列目标", requires_target=True, requires_time=True, supports_gpu=True, parameters=SEQUENCE_PARAMETERS),
    _definition("gru_regressor", "GRU 序列回归", "sequence_regression", "循环神经网络", "使用门控循环单元预测连续序列目标", requires_target=True, requires_time=True, supports_gpu=True, parameters=SEQUENCE_PARAMETERS),
    _definition("rnn_classifier", "RNN 序列分类", "sequence_classification", "循环神经网络", "使用普通循环单元预测序列类别", requires_target=True, requires_time=True, supports_gpu=True, parameters=SEQUENCE_PARAMETERS),
    _definition("lstm_classifier", "LSTM 序列分类", "sequence_classification", "循环神经网络", "使用长短期记忆单元预测序列类别", requires_target=True, requires_time=True, supports_gpu=True, parameters=SEQUENCE_PARAMETERS),
    _definition("gru_classifier", "GRU 序列分类", "sequence_classification", "循环神经网络", "使用门控循环单元预测序列类别", requires_target=True, requires_time=True, supports_gpu=True, parameters=SEQUENCE_PARAMETERS),

    # Planned algorithms keep the catalog complete while the UI prevents unsupported execution.
    _definition("knn_classifier", "K 近邻分类", "classification", "邻近模型", "根据邻近样本完成分类", requires_target=True, dependencies=["scikit-learn"], chart_templates=["confusion_matrix"]),
    _definition("naive_bayes_classifier", "朴素贝叶斯分类", "classification", "概率模型", "基于条件独立假设完成分类", requires_target=True, dependencies=["scikit-learn"], chart_templates=["confusion_matrix"]),
    _definition("svm_classifier", "支持向量机分类", "classification", "核方法", "使用最大间隔分类超平面", requires_target=True, dependencies=["scikit-learn"], chart_templates=["confusion_matrix"]),
    _definition("linear_discriminant_classifier", "线性判别分析", "classification", "判别分析", "在类间和类内方差之间寻找判别方向", requires_target=True, dependencies=["scikit-learn"], chart_templates=["confusion_matrix"]),
    _definition("quadratic_discriminant_classifier", "二次判别分析", "classification", "判别分析", "使用每个类别独立协方差矩阵完成分类", requires_target=True, dependencies=["scikit-learn"], chart_templates=["confusion_matrix"]),
    _definition("gradient_boosting_classifier", "梯度提升分类", "classification", "梯度提升", "通过逐步拟合残差完成分类", requires_target=True, dependencies=["scikit-learn"], chart_templates=["confusion_matrix", "feature_importance"]),
    _definition("elastic_net_regressor", "ElasticNet 回归", "regression", "线性模型", "结合 L1 和 L2 正则化的回归", requires_target=True, dependencies=["scikit-learn"], chart_templates=["scatter", "residual"], parameters=ELASTIC_NET_PARAMETERS),
    _definition("lasso_regressor", "Lasso 回归", "regression", "线性模型", "使用 L1 正则化筛选特征", requires_target=True, dependencies=["scikit-learn"], chart_templates=["scatter", "residual", "feature_importance"], parameters=REGULARIZATION_PARAMETERS),
    _definition("huber_regressor", "Huber 回归", "regression", "稳健回归", "降低异常值对回归结果的影响", requires_target=True, dependencies=["scikit-learn"], chart_templates=["scatter", "residual"], parameters=HUBER_PARAMETERS),
    _definition("svm_regressor", "支持向量回归", "regression", "核方法", "使用间隔损失预测连续目标", requires_target=True, dependencies=["scikit-learn"], chart_templates=["scatter", "residual"]),
    _definition("decision_tree_regressor", "决策树回归", "regression", "树模型", "使用单棵决策树预测连续目标", requires_target=True, dependencies=["scikit-learn"], chart_templates=["scatter", "feature_importance"], parameters=[TREE_PARAMETERS[1]]),
    _definition("gradient_boosting_regressor", "梯度提升回归", "regression", "梯度提升", "通过逐步拟合残差预测连续目标", requires_target=True, dependencies=["scikit-learn"], chart_templates=["scatter", "residual", "feature_importance"]),
    _definition("knn_regressor", "K 近邻回归", "regression", "邻近模型", "根据邻近样本预测连续值", requires_target=True, dependencies=["scikit-learn"], chart_templates=["scatter", "residual"]),
    _definition("bagging_regressor", "Bagging 回归", "regression", "集成学习", "通过自助采样集成多个基学习器", requires_target=True, dependencies=["scikit-learn"], chart_templates=["scatter", "feature_importance"]),
    _definition("lightgbm_regressor", "LightGBM 回归", "regression", "梯度提升", "面向大规模表格数据的梯度提升回归", requires_target=True, dependencies=["lightgbm"], chart_templates=["scatter", "residual", "feature_importance"]),
    _definition("poisson_regressor", "Poisson 回归", "regression", "广义线性模型", "适合计数目标的广义线性回归", requires_target=True, dependencies=["scikit-learn"], chart_templates=["scatter", "residual"], parameters=REGULARIZATION_PARAMETERS),
    _definition("quantile_regressor", "分位数回归", "regression", "稳健统计", "估计条件分位数和预测区间", requires_target=True, dependencies=["scikit-learn"], chart_templates=["scatter", "residual"], parameters=QUANTILE_PARAMETERS),
    _definition("kmedoids", "K-Medoids", "clustering", "中心点聚类", "使用真实样本作为聚类中心", dependencies=["numpy"], chart_templates=["cluster_scatter", "heatmap"], parameters=CLUSTER_COUNT),
    _definition("fuzzy_cmeans", "Fuzzy C-Means", "clustering", "软聚类", "为样本分配多个聚类隶属度", dependencies=["numpy"], chart_templates=["cluster_scatter", "heatmap"], parameters=CLUSTER_COUNT),
    _definition("optics", "OPTICS", "clustering", "密度聚类", "从多种密度尺度提取聚类结构", dependencies=["scikit-learn"], chart_templates=["cluster_scatter"], parameters=DENSITY_PARAMETERS),
    _definition("spectral_clustering", "谱聚类", "clustering", "图聚类", "基于相似度图的聚类方法", dependencies=["scikit-learn"], chart_templates=["cluster_scatter"], parameters=CLUSTER_COUNT),
    _definition("one_sample_t_test", "单样本 t 检验", "hypothesis_test", "假设检验", "检验样本均值是否等于给定值", requires_target=True, dependencies=["scipy"], chart_templates=["boxplot"], parameters=TEST_PARAMETERS),
    _definition("independent_t_test", "独立样本 t 检验", "hypothesis_test", "假设检验", "比较两个独立样本的均值", requires_target=True, requires_factors=True, dependencies=["scipy"], chart_templates=["boxplot"]),
    _definition("paired_t_test", "配对样本 t 检验", "hypothesis_test", "假设检验", "比较配对样本的均值差异", requires_target=True, dependencies=["scipy"], chart_templates=["boxplot"]),
    _definition("chi_square_test", "卡方独立性检验", "hypothesis_test", "假设检验", "检验两个分类变量是否独立", requires_factors=True, dependencies=["scipy"], chart_templates=["heatmap"]),
    _definition("pca", "主成分分析", "dimensionality_reduction", "降维分析", "提取数值特征的主要变化方向", dependencies=["scikit-learn"], chart_templates=["scatter", "heatmap"]),
    _definition("tsne", "t-SNE", "dimensionality_reduction", "降维分析", "用于探索高维样本局部结构", dependencies=["scikit-learn"], chart_templates=["scatter"]),
    _definition("truncated_svd", "Truncated SVD", "dimensionality_reduction", "降维分析", "对稀疏或高维矩阵进行截断奇异值分解", dependencies=["scikit-learn"], chart_templates=["scatter"]),
    _definition("umap", "UMAP", "dimensionality_reduction", "降维分析", "保持局部结构的非线性降维方法", dependencies=["umap-learn"], chart_templates=["scatter"]),
    _definition("missing_value_profile", "缺失值分析", "exploration", "数据探索", "统计每个字段的缺失情况", dependencies=["pandas"], chart_templates=["bar", "heatmap"]),
    _definition("correlation_profile", "相关性分析", "exploration", "数据探索", "计算数值字段之间的相关关系", dependencies=["pandas"], chart_templates=["heatmap"]),
]

ALGORITHM_BY_ID = {algorithm.id: algorithm for algorithm in ALGORITHMS}

LEGACY_METHOD_DEFAULTS = {
    "classification": "random_forest_classifier",
    "regression": "random_forest_regressor",
    "clustering": "kmeans",
    "anova": "one_way_anova",
    "deep-learning": "lstm_regressor",
}


def resolve_algorithm_id(algorithm_id: str | None, legacy_method: str | None) -> str:
    resolved = algorithm_id or LEGACY_METHOD_DEFAULTS.get(legacy_method or "")
    if not resolved or resolved not in ALGORITHM_BY_ID:
        raise ValueError(f"未知算法: {algorithm_id or legacy_method or '未指定'}")
    return resolved


def normalize_parameters(
    algorithm_id: str,
    supplied: dict[str, bool | int | float | str],
) -> dict[str, bool | int | float | str]:
    definition = ALGORITHM_BY_ID[algorithm_id]
    available = {parameter.id: parameter for parameter in definition.parameters}
    unknown = sorted(set(supplied) - set(available))
    if unknown:
        raise ValueError(f"算法 {algorithm_id} 不支持参数: {', '.join(unknown)}")

    normalized: dict[str, bool | int | float | str] = {}
    for parameter_id, parameter in available.items():
        value = supplied.get(parameter_id, parameter.default)
        if parameter.value_type == "integer":
            if isinstance(value, bool) or not isinstance(value, (int, float)) or int(value) != value:
                raise ValueError(f"参数 {parameter_id} 必须是整数")
            value = int(value)
        elif parameter.value_type == "number":
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ValueError(f"参数 {parameter_id} 必须是数值")
            value = float(value)
        elif parameter.value_type == "boolean" and not isinstance(value, bool):
            raise ValueError(f"参数 {parameter_id} 必须是布尔值")
        elif parameter.value_type == "select" and str(value) not in parameter.options:
            raise ValueError(f"参数 {parameter_id} 必须是以下选项之一: {', '.join(parameter.options)}")
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            if parameter.minimum is not None and value < parameter.minimum:
                raise ValueError(f"参数 {parameter_id} 不能小于 {parameter.minimum}")
            if parameter.maximum is not None and value > parameter.maximum:
                raise ValueError(f"参数 {parameter_id} 不能大于 {parameter.maximum}")
        normalized[parameter_id] = value
    return normalized


def get_algorithm_catalog() -> AlgorithmCatalog:
    return AlgorithmCatalog(algorithms=ALGORITHMS)
