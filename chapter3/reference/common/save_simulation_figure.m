function save_simulation_figure(fig, filename)
%SAVE_SIMULATION_FIGURE Stable, headless report figure export.
exportgraphics(fig, filename, 'Resolution', 160);
close(fig);
end
