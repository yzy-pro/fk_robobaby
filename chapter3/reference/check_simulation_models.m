function check_simulation_models()
%CHECK_SIMULATION_MODELS Analytic checks independent of the demo images.
cfg=simulation_config();
% Bilinear must exactly reproduce a plane at interior fractional locations.
[u,v]=meshgrid(1:12,1:10); plane=uint8(3*u+5*v+7);
[got,valid]=sample_image(plane,[2.25,6.5],[3.5,7.25],'bilinear');
expected=uint8(3*[2.25,6.5]+5*[3.5,7.25]+7);
assert(all(valid) && isequal(got,expected),'Bilinear plane reproduction failed.');
% Out-of-frame coordinates must stay invalid, not wrap unsigned or clamp.
[got,valid]=sample_image(plane,[-1,NaN,12],[2,2,10],'bilinear');
assert(isequal(valid,[false,false,true]) && got(1)==0 && got(2)==0 && got(3)==plane(10,12));
cfg.radial=[0,0]; cfg.tangential=[0,0];
[mx,my]=inverse_camera_map([10,12],cfg,eye(3),true);
identity=sample_image(plane,mx,my,'bilinear');
assert(isequal(identity,plane),'Zero distortion must preserve the full image.');
% Nonzero tangential coefficients checked against hand-computed x=.2,y=-.1.
cfg.K=[10,0,1;0,10,1;0,0,1];cfg.tangential=[.03,-.02];
[mx,my]=inverse_camera_map([3,4],cfg,eye(3),true);
% At u=3,v=2: x=.2,y=.1,r2=.05; dx=-.0014, dy=.0013.
assert(abs(mx(2,3)-(3-.014))<1e-12 && abs(my(2,3)-(2+.013))<1e-12, ...
    'Nonzero tangential distortion formula failed.');
R=pose_rotation(.2,-.1); assert(norm(R'*R-eye(3),'fro')<1e-12 && det(R)>0);
% A dark sequence must start at identity and follow causal two-frame confirm.
state=gamma_state(); actual=zeros(1,6);
for k=1:6
    [~,state,info]=adaptive_gamma_frame(uint8(20*ones(4,6,3)),state);
    actual(k)=info.active;
end
assert(isequal(actual,[3,3,3,2,1,0]),'Gamma frame latency/confirmation is wrong.');
input=uint8(128*ones(4,8,3));
[output,~,info]=adaptive_gamma_frame(input,gamma_state());
assert(isequal(input,output) && info.classified==3,'Gamma identity failed.');
input(:,1:4,:)=0;input(:,5:8,:)=255;
[~,~,info]=adaptive_gamma_frame(input,gamma_state());
assert(info.classified==2,'Mixed-light priority failed.');
% Every threshold: equality at 144,176,208 uses strict > on the bright side.
levels=[47,48,79,80,111,112,144,145,176,177,208,209];
classes=[0,1,1,2,2,3,3,4,4,5,5,6];
for k=1:numel(levels)
    [~,~,info]=adaptive_gamma_frame(uint8(levels(k)*ones(2,2,3)),gamma_state());
    assert(info.classified==classes(k),'Gamma threshold boundary failed.');
end
cfg=simulation_config();
lut=uint8(floor(255*((0:255)'/255).^cfg.gammaExponents+0.5));
assert(all(lut(1,:)==0) && all(lut(end,:)==255) && all(diff(double(lut))>=0,'all'));
% Cross-check all LUT entries with actual RTL ROM, when sibling project exists.
rtl=fullfile(fileparts(fileparts(fileparts(cfg.root))),'Pgl50h','src','video', ...
    'preprocess','adaptive_gamma_lut.v');
if isfile(rtl)
    tokens=regexp(fileread(rtl),'rom\[(\d+)\]=8''d(\d+);','tokens');
    for k=1:numel(tokens)
        address=str2double(tokens{k}{1}); value=str2double(tokens{k}{2});
        curve=floor(address/256);
        if curve<7, assert(value==lut(mod(address,256)+1,curve+1)); end
    end
    assert(numel(tokens)==2048,'RTL LUT parsing failed.');
end
fprintf('PASS: bilinear, borders, tangential model, rotation, gamma thresholds/causality/LUT.\n');
end
