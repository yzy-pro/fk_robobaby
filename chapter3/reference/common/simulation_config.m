function cfg = simulation_config()
%SIMULATION_CONFIG Reproducible camera and numerical conventions.
root = fileparts(fileparts(mfilename('fullpath')));
cfg.root = root;
cfg.figures = fullfile(fileparts(root), 'figures');
cfg.results = fullfile(root, 'results');
cfg.image = fullfile(root, 'undistort', 'images', '20260923_125558_900.jpg');
% Column-vector intrinsics; MATLAB pixel centres start at ONE.
cfg.K = [748.4469, 0, 944.9033; 0, 748.0773, 522.3963; 0, 0, 1];
cfg.radial = [0.0099, -0.0434];
cfg.tangential = [0, 0];
cfg.imageSize = [1080, 1920];
cfg.depthEpsilon = 1024 / 2^18;
cfg.maxRadiusSquared = 600000 / 2^18;
cfg.gammaExponents = [0.50, 0.65, 0.80, 1, 1.25, 1.55, 1.90];
if ~isfolder(cfg.figures), mkdir(cfg.figures); end
if ~isfolder(cfg.results), mkdir(cfg.results); end
end
