# 第五章仿真证据

`run_simulations.py` 复用 Pgl50h 的 11 个现有 SystemVerilog 测试平台，
只读 FPGA 工程，将编译文件放入临时目录，将证据写入本目录。
需要 Python 3、Icarus Verilog 及 vvp；不依赖额外 Python 包。

在报告根目录运行：

```sh
python3 chapter5/references/run_simulations.py
python3 chapter5/references/make_waveforms.py
```

工程路径默认为与 report 同级的 Pgl50h，可用 `--project /path/to/Pgl50h` 修改。
复跑默认会更新 `local_20261025`；要保留本次归档，可用 `--output /tmp/chapter5_new_run`。
波形生成脚本读取 `local_20261025`，输出 `chapter5/figures/*.tex`。
两组插入的 trace 模块仅使用 `$dumpvars` 观察已有信号，不修改 DUT 或测试激励。

`local_20261025/manifest.json` 保存工具版本、实际参数、编译/执行命令、
全部编译输入的 SHA256、返回码及 PASS/MEASURE 行。临时目录中的 vvp
在运行后删除，复现时应重新编译。`*.compile.log` 为空表示编译器未输出诊断；
`*.log` 是原始运行输出，`*.vcd` 是真实信号记录，非手绘示意。
本次 11 项均通过，当前 RTL 功能复跑不等于对全部工程测试的完整回归。

分块渲染保留 320×180 的源图像和测试内参，只计算左上 144×40 的输出区域，
使用 128×32 块。五组姿态各比较 5760 个像素；日志中的 fps 是小区域循环耗时的倒数，
正文没有把它作为整幅视频帧率。参考坐标与 DUT 共用逆映射实现，像素比较主要验证
调度、缓存和采样路径，不能当作独立光学精度测量。

正文另行引用的历史证据在只读 FPGA 工程中：

| 证据 | 相对于 Pgl50h 的位置 | 用途 |
| --- | --- | --- |
| 2026-10-22 整帧并发 | `verification/pds_pc_control_write_ram_20261022/simulation/result.log`、`source_identity.json` | 历史 1080p 并发、像素计分板和发布事件 |
| 整帧 Gamma | `verification/pds_pc_control_write_ram_20261022/pc_control/03_tb_adaptive_gamma_1080p.log` | 历史 1080p 连续节拍和全白帧统计 |
| 2026-10-10 厂商 DDR | `verification/pose_tiled_20261010/vendor_ddr_boundary_latency/` | 控制器/PHY 与 Micron 模型的短事务边界和延迟 |

这些历史测试没有在本次重新执行。应结合各归档自己的源码快照与警告记录使用。
