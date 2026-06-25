# 菜市番茄生鲜度智能识别系统

本项目用于课程论文《菜市番茄生鲜度智能识别系统的设计与实现》的后续代码实现与材料管理。当前阶段已完成论文文档、系统图表与项目目录整理，并实现了一个可运行的番茄生鲜度识别最小版本。

## 项目目标

面向菜市场番茄质检场景，实现一个基于 Python 图像处理的番茄生鲜度识别系统。当前识别逻辑采用启发式规则，能够对番茄图像进行质量检测、图像预处理、等级识别、异常预警与检测记录保存。

## 当前状态

- 已整理课程论文最终含图版。
- 已整理 UML 用例图、业务流程图、DFD 数据流图、功能层次结构图、类图和时序图。
- 已初始化项目目录结构。
- 已初始化 Git 仓库。
- 已实现可运行的命令行识别功能。
- 已提供演示图片生成脚本和单元测试。
- 已补充合成测试集、批量评估结果和评估图表。
- 尚未实现模型训练、后端接口和前端页面。

## 计划功能

当前最小版本已覆盖以下模块：

1. 图像读取与质量检测：判断图片是否模糊、过暗或过曝。
2. 图像预处理：完成尺寸归一化、降噪、颜色通道转换和像素归一化。
3. 番茄生鲜度识别：基于颜色、暗斑、纹理等启发式特征输出优质、新鲜合格、轻微变质、严重变质四类结果。
4. 异常预警：对轻微变质和严重变质番茄生成预警信息。
5. 检测记录管理：以 JSON Lines 格式保存图像路径、识别结果、置信度和检测时间。

后续扩展模块：

1. 数据统计分析：统计检测总量、合格率和异常等级占比。
2. 后端服务接口：提供图片上传、识别、记录查询等 API。
3. 前端展示页面：展示检测结果、预警信息和统计图表。

## 技术栈规划

| 模块 | 技术 |
|------|------|
| 图像处理 | Python, Pillow, NumPy |
| 模型推理 | 当前为启发式规则，后续可替换为 TensorFlow 或 PyTorch |
| 后端服务 | Django 或 Flask |
| 数据库 | MySQL 或 SQLite |
| 前端展示 | HTML, CSS, JavaScript, ECharts |
| 文档管理 | Word, PNG 图表 |

## 项目结构

```text
TomatoFreshnessRecognition/
  README.md
  requirements.txt
  docs/
    paper/              # 课程论文最终文档
    figures/            # 论文相关图表
    evaluation/         # 批量评估数据和图表
  scripts/
    create_demo_images.py
    generate_test_dataset.py
    evaluate_test_set.py
  src/
    tomato_freshness/   # 番茄识别核心代码
  datasets/
    test_set/           # 合成测试集与标签文件
  models/               # 后续模型文件目录，当前不提交大模型文件
  tests/                # 单元测试
```

## 快速开始

1. 创建虚拟环境并安装依赖：

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. 生成演示图片：

   ```bash
   python scripts/create_demo_images.py
   ```

3. 运行单张图片识别：

   ```bash
   PYTHONPATH=src python -m tomato_freshness.cli examples/tomato_excellent.png
   ```

4. 输出 JSON 并保存检测记录：

   ```bash
   PYTHONPATH=src python -m tomato_freshness.cli examples/tomato_badly_rotten.png --json --record outputs/detect_records.jsonl
   ```

5. 运行测试：

   ```bash
   PYTHONPATH=src python -m unittest discover -s tests
   ```

6. 生成测试集并输出评估图表：

   ```bash
   PYTHONPATH=src python scripts/generate_test_dataset.py
   PYTHONPATH=src python scripts/evaluate_test_set.py
   ```

## 测试集与评估图表

当前项目提供一组合成测试集，用于演示识别流程、批量评估和论文图表展示。测试集不代表真实菜市场采集数据，主要用于课程设计阶段的功能验证。

测试集位置：

- `datasets/test_set/labels.csv`：测试集标签文件
- `datasets/test_set/excellent/`：优质番茄样本
- `datasets/test_set/qualified/`：新鲜合格番茄样本
- `datasets/test_set/slightly_rotten/`：轻微变质番茄样本
- `datasets/test_set/badly_rotten/`：严重变质番茄样本

评估输出位置：

- `docs/evaluation/predictions.csv`：每张测试图片的预测明细
- `docs/evaluation/summary_metrics.json`：总体准确率、各等级准确率、混淆矩阵和平均得分
- `docs/evaluation/confusion_matrix.png`：混淆矩阵图
- `docs/evaluation/prediction_distribution.png`：预测等级分布图
- `docs/evaluation/average_score_by_class.png`：各等级平均新鲜度得分图

当前合成测试集共 48 张图片，评估脚本输出的总体准确率约为 0.6042。由于当前版本使用启发式规则，不使用真实训练模型，因此该指标只用于流程展示，不代表最终模型能力。

## 识别逻辑说明

当前版本不使用真实训练模型，而是使用可解释的启发式规则：

- 使用红色、橙色和黄绿色像素粗略定位番茄区域。
- 检查图片亮度、对比度、清晰度和番茄区域占比。
- 统计红色比例、绿色比例、暗斑比例、棕褐区域比例和纹理边缘强度。
- 将特征映射为 0-100 的新鲜度分值，再转换为四个等级。

该方案主要用于课程演示和端到端流程验证，识别准确率暂不作为当前重点。后续接入 CNN 模型时，可以保留命令行和返回结果结构，只替换内部评分逻辑。

## 相关文档

- `docs/paper/菜市番茄生鲜度智能识别系统的设计与实现_杨佳浩_2023115226_最终含图版.docx`
- `docs/figures/fig2_1_worker_use_case.png`
- `docs/figures/fig2_2_admin_use_case.png`
- `docs/figures/fig2_3_business_flow.png`
- `docs/figures/fig2_4_dfd0.png`
- `docs/figures/fig2_5_dfd1.png`
- `docs/figures/fig3_1_hierarchy.png`
- `docs/figures/fig3_2_class_diagram.png`
- `docs/figures/fig4_1_sequence.png`

## 后续实现约定

- 已完成最小可运行版本，后续再扩展用户管理、数据库和可视化。
- 不直接提交大型数据集和训练模型，必要时在 README 中说明下载地址或放置位置。
- 每个核心功能模块需要添加清晰中文注释，便于课程验收和论文附录引用。
- 提交信息建议使用中文 Conventional Commits，例如 `feat: 初始化项目结构`。

## 许可证

本项目仅用于课程设计、学习和演示。
