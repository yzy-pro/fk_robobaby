function record = export_camera_calibration(cameraParams, outputDir)
%EXPORT_CAMERA_CALIBRATION Export a toolbox cameraParameters object for the PC.
% After exporting cameraParams from Camera Calibrator:
%   export_camera_calibration(cameraParams, 'calibration_export')
% MATLAB pixel centres are ONE based. No FPGA parameters are written here.

if nargin < 2
    outputDir = 'calibration_export';
end
assert(isa(cameraParams, 'cameraParameters'), ...
    'Expected the cameraParameters object exported by Camera Calibrator.');
if isprop(cameraParams, 'K')
    K = double(cameraParams.K); % Newer releases use column-vector convention.
else
    K = double(cameraParams.IntrinsicMatrix.');
end
radial = double(cameraParams.RadialDistortion(:).');
tangential = double(cameraParams.TangentialDistortion(:).');
imageSize = double(cameraParams.ImageSize(:).');
assert(all(size(K) == [3 3]) && all(isfinite(K(:))), ...
    'The intrinsic matrix must contain finite 3-by-3 values.');
assert(K(1,1) > 0 && K(2,2) > 0 && ...
    abs(K(1,2)) < 1e-10 && abs(K(2,1)) < 1e-10 && ...
    norm(K(3,:) - [0 0 1]) < 1e-10, ...
    'Only zero-skew pinhole intrinsics are supported by this export profile.');
assert(numel(radial) == 2 && numel(tangential) == 2 && ...
    all(isfinite([radial tangential])), ...
    'Use two radial coefficients and two tangential coefficients.');
assert(numel(imageSize) == 2 && all(isfinite(imageSize)) && ...
    all(imageSize > 0) && all(imageSize == floor(imageSize)), ...
    'The calibrated image size must be specified as [height width].');

record.source = 'MATLAB Camera Calibrator export';
record.image_size_hw = imageSize;
record.intrinsic_matrix_matlab = K.';
record.radial_distortion = radial;
record.tangential_distortion = tangential;
record.pixel_coordinate_origin = 1;
record.output_intrinsics = 'same as input; no crop or resize';
record.mean_reprojection_error_px = double(cameraParams.MeanReprojectionError);
errors = double(cameraParams.ReprojectionErrors);
if ~isempty(errors)
    record.used_view_count = size(errors, 3);
    squaredDistance = sum(errors.^2, 2);
    validDistances = squaredDistance(isfinite(squaredDistance));
    if ~isempty(validDistances)
        record.reprojection_rms_px = sqrt(mean(validDistances(:)));
        record.valid_corner_observations = numel(validDistances);
    end
end

if ~isfolder(outputDir)
    mkdir(outputDir);
end
save(fullfile(outputDir, 'cameraParams.mat'), 'cameraParams');
jsonPath = fullfile(outputDir, 'camera_calibration.json');
fid = fopen(jsonPath, 'w', 'n', 'UTF-8');
assert(fid >= 0, 'Cannot open calibration JSON for writing.');
closer = onCleanup(@() fclose(fid));
fwrite(fid, jsonencode(record), 'char');
fprintf(fid, '\n');
clear closer;
fprintf('Saved MATLAB object and one-origin calibration JSON to %s\n', outputDir);
end
