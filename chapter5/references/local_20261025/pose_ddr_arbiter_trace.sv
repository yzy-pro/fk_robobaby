module chapter5_trace;
initial begin
$dumpfile("pose_ddr_arbiter.vcd");
$dumpvars(0, tb_pose_ddr_arbiter.clk, tb_pose_ddr_arbiter.axi_awvalid, tb_pose_ddr_arbiter.axi_awready, tb_pose_ddr_arbiter.axi_awlen, tb_pose_ddr_arbiter.axi_wready, tb_pose_ddr_arbiter.axi_wlast, tb_pose_ddr_arbiter.write_beat_index, tb_pose_ddr_arbiter.cap_w_done, tb_pose_ddr_arbiter.render_w_done, tb_pose_ddr_arbiter.protocol_error);
end
endmodule
