# 任意角度畸变矫正系统报告模板

本模板依据本目录 `problem.md` 和 `../Pgl50h/` 实际工程编写，使用 2026-10-22 CP2102 候选及归档记录作为主要基线。正文已填入设计说明、公式、模块映射和已有验证数据，蓝色“待补充”及图片框用于补齐团队信息、标定过程和实板测评。

## 文档结构

| 文件 | 内容 |
| --- | --- |
| `main.tex` | 封面、样式、目录及章节入口 |
| `frontmatter/abstract.tex` | 使用说明与摘要初稿 |
| `chapter1/introduction.tex` | 背景、赛题要求、指标及验收口径 |
| `chapter2/system.tex` | 平台、默认配置、系统结构与方案选择 |
| `chapter3/algorithm.tex` | 标定、坐标约定、姿态逆投影、畸变、重采样与定点格式 |
| `chapter4/hardware.tex` | 模块、帧槽、分块缓存、DDR、CDC 与时序约束 |
| `chapter5/control.tex` | IMU、CP2102、帧原子控制、Gamma 与遥测 |
| `chapter6/verification.tex` | 分层验证、当前仿真记录、实板步骤及演示方案 |
| `chapter7/performance.tex` | 帧率、延迟、带宽、资源、版本对比及画质测试表 |
| `chapter8/conclusion.tex` | 总结、赛题完成状态、局限与改进 |
| `references.tex` | 工程资料及待完善的参考文献 |
| `appendices/evidence.tex` | 源码/报告证据索引、位流身份与提交清单 |

## 编译

使用 XeLaTeX（不需要修改 FPGA 工程）：

```bash
latexmk -xelatex -interaction=nonstopmode -halt-on-error main.tex
```

输出为 `main.pdf`。已设置中文字体为 Noto Serif CJK SC / Noto Sans CJK SC / Noto Sans Mono CJK SC；如在其他系统使用，请先安装这些字体，或在 `main.tex` 中替换为本机字体。西文字体使用 TeX Gyre Termes、TeX Gyre Heros 和 Latin Modern Mono。架构图由 TikZ 直接生成，图片占位不依赖外部文件。

## 填写顺序

1. 完善封面与第 1 章指标，确认最终使用的相机、IMU、开发板及位流版本。
2. 补齐第 3 章标定原始资料、安装方向和独立浮点精度对比。
3. 按第 6 章测试步骤填写实板结果，再更新第 7 章帧率、延迟、资源与画质表。
4. 用真实照片、波形和曲线替换 `\figplaceholder`，保持标题与条件信息。
5. 更新摘要、结论和附录，删除蓝色提示，检查全部 `\fillin`、`\guide` 和占位图片均已处理。

可查找所有待处理位置：

```bash
rg -n '\\(fillin|guide|figplaceholder)\{' frontmatter chapter* appendices references.tex
```

当前数据需保持的口径：

- 128×32、默认最近邻、yaw/pitch 每轴约 ±15°，roll 未参与。历史 128×64 或串行双线性结果应单独标注。
- 60 Hz 为视频扫描；30.000030 fps 为已有行为模型的新结果发布率。
- 当前最慢观测渲染 33.14614 ms，距离 30 fps 预算约 0.18719 ms；这不是端到端延迟或全部条件的最坏保证。
- 实现工具结果与实板测量分开。归档候选未烧录、未板测；模板整理未重新运行 FPGA 综合、布局布线或 RTL 回归。
- 资源表区分综合、最终物理占用及是否包含 I/O 等统计范围。

本目录仅新增报告内容，`problem.md`、`problem.pdf` 和相邻 FPGA 工程保留原状。
