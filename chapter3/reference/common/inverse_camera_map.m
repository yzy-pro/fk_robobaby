function [mapX, mapY, valid] = inverse_camera_map(imageSize, cfg, R, lensEnabled)
%INVERSE_CAMERA_MAP Compose rotation and lens distortion before sampling.
% All maps are signed DOUBLE in one-based source pixel coordinates.
% This is a floating-point reference, not a bit-exact RTL model.
if nargin < 3, R = eye(3); end
if nargin < 4, lensEnabled = true; end
validateattributes(R, {'double'}, {'size', [3,3], 'real', 'finite'});
assert(norm(R'*R-eye(3), 'fro') < 1e-9 && abs(det(R)-1) < 1e-9, ...
    'inverse_camera_map:Rotation', 'R must be a proper rotation.');
[u,v] = meshgrid(1:imageSize(2), 1:imageSize(1));
x = (u-cfg.K(1,3))/cfg.K(1,1);
y = (v-cfg.K(2,3))/cfg.K(2,2);
X = R(1,1)*x + R(1,2)*y + R(1,3);
Y = R(2,1)*x + R(2,2)*y + R(2,3);
Z = R(3,1)*x + R(3,2)*y + R(3,3);
valid = Z > cfg.depthEpsilon;
Z(~valid) = NaN;
x = X./Z; y = Y./Z;
if lensEnabled
    r2 = x.^2+y.^2;
    valid = valid & r2 <= cfg.maxRadiusSquared;
    scale = 1 + cfg.radial(1)*r2 + cfg.radial(2)*r2.^2;
    p1 = cfg.tangential(1); p2 = cfg.tangential(2);
    xd = x.*scale + 2*p1*x.*y + p2*(r2+2*x.^2);
    yd = y.*scale + p1*(r2+2*y.^2) + 2*p2*x.*y;
else
    xd = x; yd = y;
end
mapX = cfg.K(1,1)*xd+cfg.K(1,3);
mapY = cfg.K(2,2)*yd+cfg.K(2,3);
mapX(~valid) = NaN; mapY(~valid) = NaN;
end
