function state = gamma_state()
%GAMMA_STATE Curve identifiers are ZERO-based, matching the FPGA.
state.active = 3;
state.target = 3;
state.candidate = 3;
state.candidateSeen = false;
state.pendingClass = 3;
state.pendingValid = false;
end
