function run_all_simulations()
%RUN_ALL_SIMULATIONS MATLAB batch entry; independent of current directory.
root=fileparts(mfilename('fullpath'));
addpath(fullfile(root,'common'),fullfile(root,'undistort'), ...
    fullfile(root,'pose'),fullfile(root,'gamma'));
cfg=simulation_config();
diary(fullfile(cfg.results,'matlab_run.log'));
cleanup=onCleanup(@() diary('off')); %#ok<NASGU>
fprintf('MATLAB %s\n',version);
check_simulation_models();
undistort=run_undistort_simulation();
pose=run_pose_simulation();
gamma=run_gamma_simulation();
save(fullfile(cfg.results,'simulation_summary.mat'),'undistort','pose','gamma');
fprintf('All simulations completed. Figures: %s\n',cfg.figures);
end
