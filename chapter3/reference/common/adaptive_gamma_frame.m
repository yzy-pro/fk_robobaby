function [output, state, info] = adaptive_gamma_frame(input, state, enabled)
%ADAPTIVE_GAMMA_FRAME Causal frame-level reference of adaptive_gamma_stream.v.
% Start frame: step active toward OLD target, THEN classify the PREVIOUS
% frame. A newly confirmed target can affect active no earlier than next SOF.
% It omits pixel pipeline cycles and assumes nonempty frames/normal blanking.
if nargin < 2 || isempty(state), state = gamma_state(); end
if nargin < 3, enabled = true; end
validateattributes(input, {'uint8'}, {'nonempty'});
assert(size(input,3)==3, 'Gamma input must be RGB888.');
cfg = simulation_config();
state.active = state.active + sign(state.target-state.active);
info.active = state.active;
info.targetAtStart = state.target;
if state.pendingValid
    if state.candidateSeen && state.candidate == state.pendingClass
        state.target = state.pendingClass;
    end
    state.candidate = state.pendingClass;
    state.candidateSeen = true;
end
lut = uint8(floor(255*((0:255)/255).^cfg.gammaExponents(state.active+1)+0.5));
if enabled
    output = reshape(lut(double(input(:))+1), size(input));
else
    output = input;
end
raw = double(input);
y = floor((raw(:,:,1)+2*raw(:,:,2)+raw(:,:,3))/4);
info.count = numel(y); info.sum = sum(y(:));
info.dark = nnz(y<48); info.highlight = nnz(y>=208);
info.meanInput = info.sum/info.count;
enhanced = double(output);
info.meanOutput = mean(floor((enhanced(:,:,1)+2*enhanced(:,:,2)+enhanced(:,:,3))/4),'all');
% Mixed-light rule takes priority over mean-based thresholds.
if info.dark*8 >= info.count && info.highlight*8 >= info.count
    classified = 2;
elseif info.sum < 48*info.count
    classified = 0;
elseif info.sum < 80*info.count
    classified = 1;
elseif info.sum < 112*info.count
    classified = 2;
elseif info.sum > 208*info.count
    classified = 6;
elseif info.sum > 176*info.count
    classified = 5;
elseif info.sum > 144*info.count
    classified = 4;
else
    classified = 3;
end
state.pendingClass = classified;
state.pendingValid = true;
info.classified = classified; info.targetAfter = state.target;
info.exponent = cfg.gammaExponents(state.active+1);
info.enabled = enabled;
end
