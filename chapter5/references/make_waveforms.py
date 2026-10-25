#!/usr/bin/env python3
"""Draw chapter 5 TikZ waveforms directly from the recorded VCD transitions."""
from pathlib import Path

HERE = Path(__file__).resolve().parent


def read_vcd(path):
    signals, codes = {}, {}
    time = 0
    for line in path.read_text().splitlines():
        if line.startswith("$var"):
            _, _, width, code, name, *_ = line.split()
            codes[code] = name
            signals[name] = {"width": int(width), "events": []}
        elif line.startswith("#"):
            time = int(line[1:]) / 1000  # Both recorded traces declare 1 ps.
        elif line.startswith("b"):
            value, code = line[1:].split()
            signals[codes[code]]["events"].append((time, value))
        elif line and line[0] in "01xz" and line[1:] in codes:
            signals[codes[line[1:]]]["events"].append((time, line[0]))
    return signals


def draw(name, names, start, end, ticks, annotations):
    signals = read_vcd(HERE / "local_20261025" / (name + ".vcd"))
    scale = 11 / (end - start)
    out = ["% Generated from actual VCD by references/make_waveforms.py.",
           r"\begin{tikzpicture}[x=1cm,y=1cm,font=\scriptsize]",
           r"\tikzset{trace/.style={draw=TemplateBlue,line width=0.65pt}}"]
    bottom = -0.60 * (len(names) - 1)
    for t in ticks:
        x = (t - start) * scale
        out += [fr"\draw[gray!25] ({x:.5f},{bottom-0.15:.3f}) -- ({x:.5f},0.75);",
                fr"\node[anchor=south] at ({x:.5f},0.76) {{{t:g}}};"]
    out.append(r"\node[anchor=west] at (11.15,0.87) {ns};")
    for index, key in enumerate(names):
        y = -0.60 * index
        signal = signals[key]
        before = [v for t, v in signal["events"] if t <= start]
        events = [(start, before[-1] if before else "x")]
        events += [(t, v) for t, v in signal["events"] if start < t < end]
        events += [(end, events[-1][1])]
        label = key.replace("_", r"\_")
        out.append(fr"\node[anchor=east] at (-0.15,{y+0.16:.3f}) {{\texttt{{{label}}}}};")
        if signal["width"] == 1:
            points = []
            for (t, value), (next_t, _) in zip(events, events[1:]):
                level = y + (0.32 if value == "1" else 0)
                points += [f"({(t-start)*scale:.5f},{level:.3f})",
                           f"({(next_t-start)*scale:.5f},{level:.3f})"]
            out.append(r"\draw[trace] " + " -- ".join(points) + ";")
        else:
            for (t, value), (next_t, _) in zip(events, events[1:]):
                x1, x2 = (t-start)*scale, (next_t-start)*scale
                mid = y+0.16
                tip = min(0.06, (x2-x1)/3)
                out.append(fr"\draw[trace] ({x1:.5f},{mid:.3f}) -- ({x1+tip:.5f},{y+.32:.3f}) -- ({x2-tip:.5f},{y+.32:.3f}) -- ({x2:.5f},{mid:.3f}) -- ({x2-tip:.5f},{y:.3f}) -- ({x1+tip:.5f},{y:.3f}) -- cycle;")
                text = value if any(c in value for c in "xz") else f"{int(value,2):0{(signal['width']+3)//4}X}"
                if x2-x1 > 0.40:
                    out.append(fr"\node at ({(x1+x2)/2:.5f},{mid:.3f}) {{\texttt{{{text}}}}};")
    for t, text in annotations:
        x = (t-start)*scale
        out += [fr"\draw[red!65!black,densely dashed] ({x:.5f},{bottom-.15:.3f}) -- ({x:.5f},.46);",
                fr"\node[anchor=south,text=red!65!black] at ({x:.5f},.46) {{{text}}};"]
    out.append(r"\end{tikzpicture}")
    target = HERE.parent / "figures" / (name + ".tex")
    target.parent.mkdir(exist_ok=True)
    target.write_text("\n".join(out) + "\n")


if __name__ == "__main__":
    draw("attitude_cdc", ["src_clk", "dst_clk", "toggle", "sy", "dy",
                          "sp", "dp", "sr", "dr", "valid"],
         140, 210, [140, 150, 160, 170, 180, 190, 200, 210],
         [(178.451, r"$t_{\rm valid}$")])
    draw("pose_ddr_arbiter", ["axi_awvalid", "axi_awready", "axi_awlen",
                              "axi_wready", "axi_wlast", "write_beat_index",
                              "cap_w_done", "protocol_error"],
         740, 1100, [740, 800, 860, 920, 980, 1040, 1100],
         [(815, "beat 0"), (935, "beat 1"), (1075, "beat 2")])
