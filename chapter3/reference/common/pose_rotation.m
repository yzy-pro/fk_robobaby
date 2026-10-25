function R = pose_rotation(yaw, pitch)
%POSE_ROTATION Ideal output ray -> source camera ray; angles in radians.
% Camera coordinates: x right, y down, z forward. R = Rx(pitch)*Ry(yaw).
% The camera-to-reference orientation is C=R'=Ry(-yaw)*Rx(-pitch).
validateattributes(yaw, {'numeric'}, {'scalar', 'real', 'finite'});
validateattributes(pitch, {'numeric'}, {'scalar', 'real', 'finite'});
Ry = [cos(yaw),0,sin(yaw); 0,1,0; -sin(yaw),0,cos(yaw)];
Rx = [1,0,0; 0,cos(pitch),-sin(pitch); 0,sin(pitch),cos(pitch)];
R = Rx * Ry;
end
