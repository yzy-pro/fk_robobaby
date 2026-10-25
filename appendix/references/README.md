# 附录证据与复现

三个附录分别位于 `appendixA`、`appendixB`、`appendixC`，由 `main.tex` 在 `\appendix` 后载入。

- 附录 A 引用已有 `Pgl50h/calibration/camera_20260930.json` 与 MATLAB 参数文本。
  新增 `appendixA/export_camera_calibration.m` 保存工具箱对象与 PC 可读 JSON；
  该程序尚未在 MATLAB 中执行，不构成新的标定结果。工具箱会话、原始棋盘格和误差图需补齐。
- 附录 B 基于 STM32 采集、Mahony、温控及 USART/USB CDC 源码。
  本次仅检查源码，未编译、刷写固件或测量实物姿态精度。
- 附录 C 的两张图片从 `PC/docs/` 原样复制，均为工程演示截图。
  合成图卡指标和演示视频状态不是 FPGA 或相机实测结果。

2026-10-25 在 PC 已有虚拟环境执行：

```sh
cd /home/yzy/code/ECSDC_FPGA_2026/PC
PYTHONDONTWRITEBYTECODE=1 QT_QPA_PLATFORM=offscreen \
  XDG_CACHE_HOME=/tmp/ecsd_appendix_checks/cache \
  .venv/bin/python -B -m unittest discover -s tests -v
```

`pc_unittest_20261025.txt` 是完整输出：51 项测试，41.291 s，OK，无跳过。
测试使用模拟输入、解析图像、虚拟串口与 offscreen Qt；没有打开实际视频/串口设备。
`source_manifest_20261025.json` 记录命令、日志哈希及所读工程文件哈希；
其中 PC 的软件包和测试源码全部纳入，STM32 关键驱动/任务与标定依据一并保存身份。
清单在测试后生成，用于追溯本次附录对应的内容，不能当作已打包的源码快照或位流身份。
MATLAB 的 `K` / `IntrinsicMatrix`、重投影残差数组维度和平均误差定义，
另以本机 R2025a 随附的 `cameraParameters.m`、`CameraParametersImpl.m` 核对。
参考文献提供 MathWorks 在线入口，但本次没有成功取得对应在线页面。

另外已用 PC 的实际 `load_calibration` 解析既有标定 JSON，核对零起点主点
为 `[943.9033, 521.3963]`，尺寸为 `[1920,1080]`，没有下发 FPGA。
