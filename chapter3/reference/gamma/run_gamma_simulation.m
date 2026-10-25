function metrics = run_gamma_simulation()
%RUN_GAMMA_SIMULATION Controlled illumination sequence, causal frame control.
cfg = simulation_config(); raw = imread(cfg.image);
% Subsample for frame statistics demo only; no camera geometry used here.
raw = raw(1:4:end,1:4:end,:);
normal = uint8(50+0.6*double(raw));
dark = uint8(0.18*double(raw));
bright = uint8(215+0.15*double(raw));
mixed = dark; mid = floor(size(raw,2)/2);
mixed(:,mid+1:end,:) = bright(:,mid+1:end,:);
scenes = {normal,dark,bright,mixed};
names = {'normal','dark','bright','mixed'};
framesPerScene = 10; N = framesPerScene*numel(scenes);
scene = strings(N,1); meanInput=zeros(N,1); meanOutput=zeros(N,1);
active=zeros(N,1); target=zeros(N,1); classified=zeros(N,1);
state = gamma_state();
fig = figure('Visible','off','Position',[20,20,1450,900]);
layout=tiledlayout(fig,2,4,'TileSpacing','compact','Padding','compact');
for n = 1:N
    k = ceil(n/framesPerScene); input = scenes{k};
    [output,state,info] = adaptive_gamma_frame(input,state);
    scene(n)=names{k}; meanInput(n)=info.meanInput; meanOutput(n)=info.meanOutput;
    active(n)=info.active; target(n)=info.targetAfter; classified(n)=info.classified;
    if mod(n,framesPerScene)==0
        nexttile(layout,k); image(input); axis image off; title([names{k},': raw']);
        nexttile(layout,k+4); image(output); axis image off;
        title(sprintf('curve %d, exponent %.2f',info.active,info.exponent));
        imwrite(output,fullfile(cfg.results,['gamma_',names{k},'.png']));
    end
end
save_simulation_figure(fig,fullfile(cfg.figures,'gamma_scenes.png'));
metrics=table((1:N)',scene,meanInput,meanOutput,classified,target,active, ...
    'VariableNames',{'Frame','Scene','RawMean','EnhancedMean','Classified','Target','Active'});
writetable(metrics,fullfile(cfg.results,'gamma_metrics.csv'));
assert(all(abs(diff(active))<=1),'Gamma curve changed more than one step.');
fig=figure('Visible','off','Position',[20,20,1400,850]);
tiledlayout(2,1,'TileSpacing','compact','Padding','compact');
nexttile; plot(1:N,[meanInput,meanOutput],'LineWidth',1.5); grid on;
ylabel('Mean luma (0..255)'); legend('Raw','Enhanced','Location','best');
nexttile; stairs(1:N,[classified,target,active],'LineWidth',1.5); grid on;
xlabel('Frame'); ylabel('Curve index (0..6)'); ylim([-0.3,6.3]);
legend('Classified','Target after frame','Active during frame','Location','best');
save_simulation_figure(fig,fullfile(cfg.figures,'gamma_transition.png'));
fig=figure('Visible','off','Position',[20,20,1000,650]);
lut=floor(255*((0:255)'/255).^cfg.gammaExponents+0.5);
plot(0:255,lut,'LineWidth',1.5); grid on; axis([0,255,0,255]);
xlabel('Input'); ylabel('Output'); legend(compose('exponent %.2f',cfg.gammaExponents),'Location','southeast');
save_simulation_figure(fig,fullfile(cfg.figures,'gamma_curves.png'));
end
