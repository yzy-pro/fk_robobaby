function [output, valid] = sample_image(input, mapX, mapY, method, fractionBits, border)
%SAMPLE_IMAGE Vectorized uint8 nearest/bilinear inverse sampling.
% fractionBits=Inf: floating bilinear, rounded uint8 output.
% fractionBits=5: round fractional weights to /32, truncate accumulated value.
% border='black': reject outside coordinates; 'replicate': clamp to image.
if nargin < 4, method = 'bilinear'; end
if nargin < 5, fractionBits = Inf; end
if nargin < 6, border = 'black'; end
validateattributes(input, {'uint8'}, {'nonempty'});
validateattributes(fractionBits, {'numeric'}, {'scalar', 'real', 'nonnegative'});
assert(isinf(fractionBits) || (fractionBits == floor(fractionBits) && fractionBits <= 16));
method = validatestring(method, {'nearest','bilinear'});
border = validatestring(border, {'black','replicate'});
assert(isequal(size(mapX),size(mapY)), 'Map sizes must match.');
[h,w,c] = size(input);
valid = isfinite(mapX) & isfinite(mapY);
% Suppress only floating-point roundoff at exact image borders.
tol = 1e-9;
if strcmp(border,'black')
    valid = valid & mapX >= 1-tol & mapX <= w+tol & mapY >= 1-tol & mapY <= h+tol;
end
mapX(~valid) = 1; mapY(~valid) = 1;
mapX = min(max(mapX,1),w); mapY = min(max(mapY,1),h);
if strcmp(method,'nearest')
    index = sub2ind([h,w], floor(mapY+0.5), floor(mapX+0.5));
else
    ix = floor(mapX); iy = floor(mapY);
    a = mapX-ix; b = mapY-iy;
    if isfinite(fractionBits)
        F = 2^fractionBits;
        a = floor(a*F+0.5)/F; b = floor(b*F+0.5)/F;
    end
    i00 = sub2ind([h,w],iy,ix);
    i10 = sub2ind([h,w],iy,min(ix+1,w));
    i01 = sub2ind([h,w],min(iy+1,h),ix);
    i11 = sub2ind([h,w],min(iy+1,h),min(ix+1,w));
end
output = zeros([size(mapX),c], 'uint8');
for channel = 1:c
    plane = double(input(:,:,channel));
    if strcmp(method,'nearest')
        values = plane(index);
    else
        values = (1-a).*(1-b).*plane(i00)+a.*(1-b).*plane(i10) ...
            +(1-a).*b.*plane(i01)+a.*b.*plane(i11);
        if isfinite(fractionBits), values = floor(values); end
    end
    values(~valid) = 0;
    output(:,:,channel) = uint8(values);
end
end
