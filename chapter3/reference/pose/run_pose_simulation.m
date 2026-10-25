function metrics = run_pose_simulation()
%RUN_POSE_SIMULATION Known planar scene -> rotated camera -> rectified image.
% Synthetic plane is a controlled mathematical test, not a physical IMU test.
cfg = simulation_config(); h = cfg.imageSize(1); w = cfg.imageSize(2);
[u,v] = meshgrid(1:w,1:h);
grid = mod(floor((u-1)/80)+floor((v-1)/80),2);
base = uint8(45+170*grid);
reference = cat(3,base,uint8(double(base).*(0.65+0.35*u/w)), ...
    uint8(double(base).*(0.65+0.35*v/h)));
border = mod(u-1,80)<3 | mod(v-1,80)<3;
for c = 1:3
    p = reference(:,:,c); p(border) = 240; reference(:,:,c) = p;
end
poses = [0,0; 10,0; 0,-10; 10,-8; -15,15; 15,-15];
count = size(poses,1); validRatio = zeros(count,1); rmse = zeros(count,1);
mapRMSE = zeros(count,1); qAngleMapRMSE = zeros(count,1);
samples = zeros(count,1);
fig = figure('Visible','off','Position',[20,20,1600,900]);
layout = tiledlayout(fig,2,3,'TileSpacing','compact','Padding','compact');
for k = 1:count
    R = pose_rotation(deg2rad(poses(k,1)),deg2rad(poses(k,2)));
    % Synthesize source: source ray -> reference plane, with R inverse.
    [sx,sy] = inverse_camera_map([h,w],cfg,R',false);
    [source,sourceValid] = sample_image(reference,sx,sy,'bilinear');
    [mx,my] = inverse_camera_map([h,w],cfg,R,false);
    [corrected,valid] = sample_image(source,mx,my,'bilinear');
    % Require all four source samples to be real scene data, not fill pixels.
    ix = min(max(floor(mx),1),w); iy = min(max(floor(my),1),h);
    ix(~isfinite(ix))=1; iy(~isfinite(iy))=1;
    common = valid & sourceValid(sub2ind([h,w],iy,ix)) ...
        & sourceValid(sub2ind([h,w],iy,min(ix+1,w))) ...
        & sourceValid(sub2ind([h,w],min(iy+1,h),ix)) ...
        & sourceValid(sub2ind([h,w],min(iy+1,h),min(ix+1,w)));
    d = double(corrected)-double(reference);
    mask = repmat(common,1,1,3);
    rmse(k) = sqrt(mean(d(mask).^2)); validRatio(k) = mean(common(:));
    % Independent homogeneous matrix composition must return original ray.
    Hi = cfg.K*R'/cfg.K;
    uv = [u(common)';v(common)';ones(1,nnz(common))];
    roundtrip = Hi*[mx(common)';my(common)';ones(1,nnz(common))];
    roundtrip = roundtrip(1:2,:)./roundtrip(3,:);
    e = roundtrip-uv(1:2,:); mapRMSE(k)=sqrt(mean(sum(e.^2,1)));
    q = round(deg2rad(poses(k,:))*2048);
    Rq = pose_rotation(q(1)/2048,q(2)/2048);
    [qx,qy] = inverse_camera_map([h,w],cfg,Rq,false);
    e = hypot(qx(common)-mx(common),qy(common)-my(common));
    qAngleMapRMSE(k) = sqrt(mean(e.^2)); samples(k)=nnz(common);
    if k==4
        imwrite(source,fullfile(cfg.results,'pose_source.png'));
        imwrite(corrected,fullfile(cfg.results,'pose_corrected.png'));
        imwrite(reference,fullfile(cfg.results,'pose_reference.png'));
        montageFig = figure('Visible','off','Position',[20,20,1600,500]);
        tiledlayout(1,3,'TileSpacing','compact','Padding','compact');
        nexttile; image(reference); axis image off; title('Reference planar chart');
        nexttile; image(source); axis image off; title('Synthetic camera: yaw=10, pitch=-8 deg');
        nexttile; image(corrected); axis image off; title('Rectified (common field only)');
        save_simulation_figure(montageFig,fullfile(cfg.figures,'pose_correction.png'));
    end
    nexttile(layout,k); image(corrected); axis image off;
    title(sprintf('yaw=%g, pitch=%g; valid=%.1f%%',poses(k,:),100*validRatio(k)));
end
metrics = table(poses(:,1),poses(:,2),validRatio,rmse,mapRMSE,qAngleMapRMSE,samples, ...
    'VariableNames',{'YawDeg','PitchDeg','CommonValidRatio','ImageRMSE', ...
    'CoordinateRoundTripRMSE','Q2048AngleMapRMSE','CommonPixels'});
writetable(metrics,fullfile(cfg.results,'pose_metrics.csv'));
save_simulation_figure(fig,fullfile(cfg.figures,'pose_sweep.png'));
assert(all(mapRMSE<1e-9),'Coordinate rotation roundtrip failed.');
end
