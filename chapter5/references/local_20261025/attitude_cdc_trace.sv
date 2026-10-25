module chapter5_trace;
initial begin
$dumpfile("attitude_cdc.vcd");
$dumpvars(0, tb_attitude_cdc.src_clk, tb_attitude_cdc.dst_clk, tb_attitude_cdc.src_rstn, tb_attitude_cdc.dst_rstn, tb_attitude_cdc.sy, tb_attitude_cdc.sp, tb_attitude_cdc.sr, tb_attitude_cdc.toggle, tb_attitude_cdc.dy, tb_attitude_cdc.dp, tb_attitude_cdc.dr, tb_attitude_cdc.valid);
end
endmodule
