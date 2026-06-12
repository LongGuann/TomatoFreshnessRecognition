# 菜市番茄生鲜度智能识别系统

本项目用于课程论文《菜市番茄生鲜度智能识别系统的设计与实现》的后续代码实现与材料管理。当前阶段已完成论文文档、系统图表与项目目录整理，暂未实现番茄识别功能代码。

## 项目目标

面向菜市场番茄质检场景，后续计划实现一个基于 Python、OpenCV 与深度学习模型的番茄生鲜度识别系统。系统目标是对番茄图像进行质量检测、图像预处理、等级识别、异常预警与检测记录管理。

## 当前状态

- 已整理课程论文最终含图版。
- 已整理 UML 用例图、业务流程图、DFD 数据流图、功能层次结构图、类图和时序图。
- 已初始化项目目录结构。
- 已初始化 Git 仓库。
- 尚未实现识别功能、模型训练、后端接口和前端页面。

## 计划功能

后续代码实现将按以下模块推进：

1. 图像读取与质量检测：判断图片是否模糊、过暗或过曝。
2. 图像预处理：完成尺寸归一化、降噪、颜色通道转换和像素归一化。
3. 番茄生鲜度识别：调用 CNN 模型输出优质、新鲜合格、轻微变质、严重变质四类结果。
4. 异常预警：对轻微变质和严重变质番茄生成预警信息。
5. 检测记录管理：保存图像路径、识别结果、置信度、检测时间和检测人员。
6. 数据统计分析：统计检测总量、合格率和异常等级占比。

## 技术栈规划

| 模块 | 技术 |
|------|------|
| 图像处理 | Python, OpenCV |
| 模型推理 | TensorFlow 或 PyTorch |
| 后端服务 | Django 或 Flask |
| 数据库 | MySQL 或 SQLite |
| 前端展示 | HTML, CSS, JavaScript, ECharts |
| 文档管理 | Word, PNG 图表 |

## 项目结构

```text
TomatoFreshnessRecognition/
  README.md
  docs/
    paper/              # 课程论文最终文档
    figures/            # 论文相关图表
  src/                  # 后续源代码目录，当前仅保留占位文件
  models/               # 后续模型文件目录，当前不提交大模型文件
  datasets/             # 后续数据集目录，当前不提交原始大数据集
  tests/                # 后续测试代码目录
```

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

- 先实现最小可运行版本，再扩展用户管理、数据库和可视化。
- 不直接提交大型数据集和训练模型，必要时在 README 中说明下载地址或放置位置。
- 每个核心功能模块需要添加清晰中文注释，便于课程验收和论文附录引用。
- 提交信息建议使用中文 Conventional Commits，例如 `feat: 初始化项目结构`。

## 许可证

本项目仅用于课程设计、学习和演示。
