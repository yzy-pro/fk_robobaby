# 第三章算法仿真

本目录提供镜头去畸变、姿态矫正和帧自适应 Gamma 的 MATLAB 参考模型。浮点几何、
5 位小数插值实验和 FPGA 实现不是同一种精度模型；本代码没有声称逐拍或逐位复现 RTL。

## MATLAB 运行

从报告根目录执行：

```matlab
addpath('chapter3/reference');
run_all_simulations;
```

命令行：

```bash
matlab -batch "addpath('chapter3/reference'); run_all_simulations"
```

也可先把 `common/` 和对应实验目录加入路径，再运行
`run_undistort_simulation`、`run_pose_simulation` 或 `run_gamma_simulation`。
`undistort/main.m` 保留为去畸变入口，可以从任意当前目录运行。

MATLAB 建议 R2021a 或更新版本（使用 `tiledlayout`、`exportgraphics` 和 `mean(...,'all')`）。
手工算法无需 Computer Vision Toolbox；若该工具箱可用，去畸变实验附加
`undistortImage` / `undistortPoints` 比较。历史 `evaluate_correction_effect.m` 需要
Image Processing Toolbox，它的默认质量阈值是实验参数，不是赛题强制门限，
也不会在统一入口中自动对自然场景图作图卡判定。

## 代码分工

| 文件 | 用途 |
| --- | --- |
| `common/simulation_config.m` | 唯一的相机参数、输入路径和输出目录 |
| `common/pose_rotation.m` | `R = Rx(pitch) * Ry(yaw)`，角度单位为弧度 |
| `common/inverse_camera_map.m` | 旋转、透视归一化、镜头模型及有效性保护 |
| `common/sample_image.m` | 最近邻、浮点/量化双线性及边界处理 |
| `common/gamma_state.m` | 初始化帧自适应状态，档位从 0 开始 |
| `common/adaptive_gamma_frame.m` | 原始亮度统计、两帧确认、每帧一档及因果延迟 |
| `check_simulation_models.m` | 解析平面插值、边界、非零切向、Gamma 边界/时序及 ROM 比较 |
| `undistort/run_undistort_simulation.m` | 实拍图去畸变、不同插值及权重量化比较 |
| `undistort/analysis.m` | 新坐标图的有效逐行访问范围分析 |
| `pose/run_pose_simulation.m` | 合成网格、六组姿态、图像误差及角度量化影响 |
| `gamma/run_gamma_simulation.m` | 正常/暗光/强光/混合光照，每段 10 帧的连续实验 |
| `verify_reference.py` | 独立 Python 数值检查，不替代 MATLAB 成功运行记录 |

`undistort_image(image,cameraParams)` 兼容入口仍接受 MATLAB 的内参对象，
现在没有隐式保存 `lut.mat` 的副作用，第二返回值提供浮点映射和有效掩码。
调用 `analysis` 前，先运行新去畸变实验生成 `results/undistort_maps.mat`。

## 参数、索引及实验范围

- 输入：`undistort/images/20260923_125558_900.jpg`，1920×1080 RGB888。
- 内参和系数来自 `undistort/para.txt`，与 `Pgl50h/calibration/camera_20260930.json` 一致。
- MATLAB 源/输出坐标均为 **1 基**，数组顺序是 `(row,column,channel)`。
  配置中的 `K` 是列向量模型，等于原 `cameraParams.IntrinsicMatrix'`。
- 两项径向系数，完整的标准切向项；默认切向系数为零。
- 映射坐标用带符号双精度保存，无效坐标用 NaN 表示；默认视场外填黑，
  最后一行/列内的有效插值重复边界邻点。该规则与 RTL 的四邻点保护不完全相同。
- 5 位权重用 `round(alpha*32)`，四项权重和为 1024，输出向下截断。
  浮点路径在转为 uint8 时四舍五入。
- 姿态单独仿真关闭镜头模型，通过理想图卡的正反旋转验证；组合映射函数支持同时启用。
  零姿态、10°/0°、0°/-10°、10°/-8°、-15°/15°、15°/-15° 共六组。
- 纯旋转模型不模拟相机平移、视差、运动模糊、滚动快门或 IMU 时间误差。
- Gamma 七档指数与 RTL 相同，首帧恒等、原始图统计、混合光照优先、连续两次分类确认。
  上一帧的统计在当前帧 SOF 后更新目标，实际曲线按 SOF 前旧目标步进，
  避免少算一帧控制延迟。模型不模拟像素流水线时钟。
- Gamma 场景采用原图间隔四倍抽样和受控亮度变换，不声称是实拍低照噪声数据。

## 结果及验证状态

MATLAB 成功执行后产生：

- `results/matlab_run.log`、`simulation_summary.mat`；
- `results/undistort_metrics.csv`、`pose_metrics.csv`、`gamma_metrics.csv`；
- `results/undistort_maps.mat` 和若干 PNG 输出；
- `../figures/undistort_comparison.png`、`pose_correction.png`、`pose_sweep.png`、
  `gamma_curves.png`、`gamma_scenes.png`、`gamma_transition.png`。

本次自动化环境中 MATLAB 启动失败，**新增 MATLAB 入口尚未成功执行**。
已执行独立 Python 交叉检查：

```bash
/usr/bin/python3 chapter3/reference/verify_reference.py
```

依赖系统 Python 的 NumPy、SciPy、Pillow、Matplotlib。
实际结果在 `results/reference_summary.json` 和 `*_reference.csv` 中；
所有 Python 生成的插图带 `_reference.png` 后缀，章节明确注明其来源。
这与 MATLAB 输出分开命名，避免把数值交叉检查当作 MATLAB 或 FPGA 实验。

## 历史资料

原 `main.m`、`undistort_image.m`、`analysis.m` 已备份到 `undistort/legacy/`。
原 MAT/BMP、LUT、图集、评估函数和 CSV 保留，未用新增结果覆盖。
部分历史图像为 1440×1080、`lut.mat` 为 1920×1080，不应混用。
原手工函数的非零切向公式和无符号坐标转换存在问题；新实现已修正，
因此不能把旧文件直接当作新程序的输出证据。
