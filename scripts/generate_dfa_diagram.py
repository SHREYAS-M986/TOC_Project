"""Generate docs/dfa_diagram.svg and docs/dfa_diagram.png from core.dfa_definition.

Draws a clean, formal state transition diagram:
- Start state marked with an incoming arrow.
- Accepting state (q4) drawn with concentric double circles.
- Self-loops, forward edges, and backward transitions clearly routed.
- Generates both standalone vector SVG and raster PNG without external binary dependencies.
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from core.dfa_definition import (
    STATES,
)

try:
    from PIL import Image, ImageDraw, ImageFont

    HAS_PIL = True
except ImportError:
    HAS_PIL = False


def generate_svg() -> str:
    """Generate professional SVG vector diagram for the 6-state DFA."""
    # State coordinates (x, y)
    coords = {
        "q0": (120, 240),
        "q1": (300, 240),
        "q2": (500, 240),
        "q3": (700, 240),
        "q4": (900, 240),
        "q_trap": (500, 430),
    }

    radius = 38
    inner_radius = 32

    svg = []
    svg.append('<?xml version="1.0" encoding="UTF-8"?>')
    svg.append(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1020 520" width="1020" height="520">'
    )
    svg.append("""  <defs>
    <marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
      <path d="M 0 1 L 10 5 L 0 9 z" fill="#3b82f6" />
    </marker>
    <marker id="arrow-trap" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M 0 1 L 10 5 L 0 9 z" fill="#ef4444" />
    </marker>
    <marker id="arrow-start" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8" markerHeight="8" orient="auto-start-reverse">
      <path d="M 0 1 L 10 5 L 0 9 z" fill="#10b981" />
    </marker>
    <style>
      .state-bg { fill: #f8fafc; stroke: #3b82f6; stroke-width: 2.5; }
      .state-accept { fill: #ecfdf5; stroke: #059669; stroke-width: 2.5; }
      .state-trap { fill: #fef2f2; stroke: #dc2626; stroke-width: 2.5; }
      .state-text { font-family: ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; font-weight: 700; font-size: 18px; text-anchor: middle; dominant-baseline: central; fill: #0f172a; }
      .state-sub { font-size: 11px; font-weight: 500; fill: #64748b; }
      .edge { fill: none; stroke: #3b82f6; stroke-width: 2; marker-end: url(#arrow); }
      .edge-trap { fill: none; stroke: #ef4444; stroke-width: 1.5; stroke-dasharray: 4,4; marker-end: url(#arrow-trap); }
      .edge-label { font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace; font-size: 12px; font-weight: 600; fill: #1e293b; text-anchor: middle; }
      .title { font-family: ui-sans-serif, system-ui, sans-serif; font-size: 20px; font-weight: 800; fill: #0f172a; }
      .subtitle { font-family: ui-sans-serif, system-ui, sans-serif; font-size: 13px; font-weight: 500; fill: #64748b; }
    </style>
  </defs>""")

    # Background canvas
    svg.append('  <rect width="1020" height="520" fill="#ffffff" rx="12" />')

    # Header Title
    svg.append(
        '  <text x="510" y="38" text-anchor="middle" class="title">Minimal DFA State Transition Diagram</text>'
    )
    svg.append(
        '  <text x="510" y="62" text-anchor="middle" class="subtitle">Pattern: [A-Za-z]+ing (Tokens ending in &quot;ing&quot; with length &gt;= 4)</text>'
    )

    # 1. Start Arrow pointing to q0
    svg.append("  <!-- Start State Arrow -->")
    svg.append(
        '  <path d="M 40 240 L 78 240" fill="none" stroke="#10b981" stroke-width="3" marker-end="url(#arrow-start)" />'
    )
    svg.append(
        '  <text x="50" y="228" font-family="sans-serif" font-size="12" font-weight="700" fill="#10b981">START</text>'
    )

    # 2. Forward transitions along the spine (q0 -> q1 -> q2 -> q3 -> q4)
    svg.append("  <!-- Forward Transitions -->")
    # q0 -> q1 on I, N, G, OTHER
    svg.append('  <path d="M 158 240 L 260 240" class="edge" />')
    svg.append(
        '  <rect x="175" y="218" width="70" height="18" fill="#ffffff" rx="4" opacity="0.9" />'
    )
    svg.append('  <text x="210" y="231" class="edge-label">I,N,G,O</text>')

    # q1 -> q2 on I
    svg.append('  <path d="M 338 240 L 460 240" class="edge" />')
    svg.append(
        '  <rect x="382" y="220" width="36" height="18" fill="#ffffff" rx="4" opacity="0.9" />'
    )
    svg.append('  <text x="400" y="233" class="edge-label">I</text>')

    # q2 -> q3 on N
    svg.append('  <path d="M 538 240 L 660 240" class="edge" />')
    svg.append(
        '  <rect x="582" y="220" width="36" height="18" fill="#ffffff" rx="4" opacity="0.9" />'
    )
    svg.append('  <text x="600" y="233" class="edge-label">N</text>')

    # q3 -> q4 on G
    svg.append('  <path d="M 738 240 L 860 240" class="edge" stroke="#059669" />')
    svg.append(
        '  <rect x="782" y="220" width="36" height="18" fill="#ffffff" rx="4" opacity="0.9" />'
    )
    svg.append('  <text x="800" y="233" class="edge-label" fill="#059669">G</text>')

    # 3. Self Loops
    # q1 self-loop on N, G, OTHER (top arc)
    svg.append("  <!-- Self Loops -->")
    svg.append('  <path d="M 285 204 C 270 140, 330 140, 315 204" class="edge" />')
    svg.append('  <text x="300" y="148" class="edge-label">N, G, O</text>')

    # q2 self-loop on I (top arc)
    svg.append('  <path d="M 485 204 C 470 140, 530 140, 515 204" class="edge" />')
    svg.append('  <text x="500" y="148" class="edge-label">I</text>')

    # q_trap self-loop on all inputs (bottom arc)
    svg.append('  <path d="M 485 468 C 470 515, 530 515, 515 468" class="edge-trap" />')
    svg.append('  <text x="500" y="508" class="edge-label" fill="#dc2626">ALL</text>')

    # 4. Backward Transitions
    svg.append("  <!-- Backward Transitions -->")
    # q2 -> q1 on G, OTHER (lower curved arc)
    svg.append('  <path d="M 480 270 C 430 320, 370 320, 320 270" class="edge" />')
    svg.append('  <text x="400" y="322" class="edge-label">G, O</text>')

    # q3 -> q1 on N, OTHER (lower curved arc)
    svg.append('  <path d="M 680 270 C 580 360, 420 360, 315 275" class="edge" />')
    svg.append('  <text x="480" y="358" class="edge-label">N, O</text>')

    # q3 -> q2 on I (upper arc)
    svg.append('  <path d="M 680 215 C 630 170, 570 170, 520 215" class="edge" />')
    svg.append('  <text x="600" y="178" class="edge-label">I</text>')

    # q4 -> q2 on I (upper arc)
    svg.append('  <path d="M 880 215 C 780 120, 620 120, 525 218" class="edge" />')
    svg.append('  <text x="700" y="128" class="edge-label">I</text>')

    # q4 -> q1 on N, G, OTHER (long lower arc)
    svg.append('  <path d="M 885 272 C 750 390, 450 390, 310 276" class="edge" />')
    svg.append('  <text x="600" y="396" class="edge-label">N, G, O</text>')

    # 5. Trap State Transitions (dashed red)
    svg.append("  <!-- Trap State Edges -->")
    svg.append('  <path d="M 140 275 C 240 430, 380 430, 460 430" class="edge-trap" />')
    svg.append(
        '  <text x="260" y="445" class="edge-label" fill="#dc2626">NON_LETTER</text>'
    )

    # 6. Draw States
    svg.append("  <!-- States -->")
    for sid, (cx, cy) in coords.items():
        st = STATES[sid]
        if st["is_accepting"]:
            # Double circle for accepting state
            svg.append(
                f'  <circle cx="{cx}" cy="{cy}" r="{radius}" class="state-accept" />'
            )
            svg.append(
                f'  <circle cx="{cx}" cy="{cy}" r="{inner_radius}" class="state-accept" />'
            )
            svg.append(
                f'  <text x="{cx}" y="{cy - 5}" class="state-text" fill="#047857">{sid}</text>'
            )
            svg.append(
                f'  <text x="{cx}" y="{cy + 14}" class="state-sub" fill="#059669">Accept</text>'
            )
        elif sid == "q_trap":
            svg.append(
                f'  <circle cx="{cx}" cy="{cy}" r="{radius - 3}" class="state-trap" />'
            )
            svg.append(
                f'  <text x="{cx}" y="{cy - 4}" class="state-text" fill="#b91c1c">{sid}</text>'
            )
            svg.append(
                f'  <text x="{cx}" y="{cy + 13}" class="state-sub" fill="#dc2626">Trap</text>'
            )
        else:
            svg.append(
                f'  <circle cx="{cx}" cy="{cy}" r="{radius}" class="state-bg" />'
            )
            svg.append(f'  <text x="{cx}" y="{cy - 4}" class="state-text">{sid}</text>')
            sub = (
                "Start"
                if st["is_start"]
                else (
                    "'i'"
                    if sid == "q2"
                    else ("'in'" if sid == "q3" else "&gt;=1 letter")
                )
            )
            svg.append(f'  <text x="{cx}" y="{cy + 13}" class="state-sub">{sub}</text>')

    svg.append("</svg>")
    return "\n".join(svg)


def generate_png_with_pillow(output_path: Path) -> None:
    """Generate clean raster PNG diagram using Pillow."""
    if not HAS_PIL:
        print("Pillow not available, skipping raster PNG rendering.")
        return

    width, height = 1020, 520
    img = Image.new("RGB", (width, height), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)

    coords = {
        "q0": (120, 240),
        "q1": (300, 240),
        "q2": (500, 240),
        "q3": (700, 240),
        "q4": (900, 240),
        "q_trap": (500, 430),
    }

    radius = 38
    inner_radius = 32

    # Draw title
    draw.text((360, 20), "Minimal DFA State Transition Diagram", fill=(15, 23, 42))
    draw.text(
        (380, 45),
        "[A-Za-z]+ing (Words ending in 'ing', length >= 4)",
        fill=(100, 116, 139),
    )

    # Draw forward arrows along spine
    # q0 -> q1
    draw.line([(158, 240), (262, 240)], fill=(59, 130, 246), width=3)
    draw.polygon([(262, 240), (254, 235), (254, 245)], fill=(59, 130, 246))
    draw.text((200, 220), "I,N,G,O", fill=(30, 41, 59))

    # q1 -> q2
    draw.line([(338, 240), (462, 240)], fill=(59, 130, 246), width=3)
    draw.polygon([(462, 240), (454, 235), (454, 245)], fill=(59, 130, 246))
    draw.text((395, 220), "I", fill=(30, 41, 59))

    # q2 -> q3
    draw.line([(538, 240), (662, 240)], fill=(59, 130, 246), width=3)
    draw.polygon([(662, 240), (654, 235), (654, 245)], fill=(59, 130, 246))
    draw.text((595, 220), "N", fill=(30, 41, 59))

    # q3 -> q4
    draw.line([(738, 240), (862, 240)], fill=(5, 150, 105), width=3)
    draw.polygon([(862, 240), (854, 235), (854, 245)], fill=(5, 150, 105))
    draw.text((795, 220), "G", fill=(5, 150, 105))

    # Start indicator arrow
    draw.line([(40, 240), (82, 240)], fill=(16, 185, 129), width=3)
    draw.polygon([(82, 240), (74, 235), (74, 245)], fill=(16, 185, 129))
    draw.text((45, 220), "START", fill=(16, 185, 129))

    # Draw states
    for sid, (cx, cy) in coords.items():
        st = STATES[sid]
        if st["is_accepting"]:
            # Outer circle
            draw.ellipse(
                [cx - radius, cy - radius, cx + radius, cy + radius],
                outline=(5, 150, 105),
                width=3,
                fill=(236, 253, 245),
            )
            # Inner circle
            draw.ellipse(
                [
                    cx - inner_radius,
                    cy - inner_radius,
                    cx + inner_radius,
                    cy + inner_radius,
                ],
                outline=(5, 150, 105),
                width=2,
            )
            draw.text((cx - 10, cy - 8), sid, fill=(4, 120, 87))
        elif sid == "q_trap":
            draw.ellipse(
                [cx - radius + 3, cy - radius + 3, cx + radius - 3, cy + radius - 3],
                outline=(220, 38, 38),
                width=3,
                fill=(254, 242, 242),
            )
            draw.text((cx - 18, cy - 8), sid, fill=(185, 28, 28))
        else:
            draw.ellipse(
                [cx - radius, cy - radius, cx + radius, cy + radius],
                outline=(59, 130, 246),
                width=3,
                fill=(248, 250, 252),
            )
            draw.text((cx - 10, cy - 8), sid, fill=(15, 23, 42))

    img.save(output_path, "PNG")
    print(f"Generated PNG raster diagram at: {output_path}")


def main() -> None:
    docs_dir = PROJECT_ROOT / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)

    svg_content = generate_svg()
    svg_path = docs_dir / "dfa_diagram.svg"
    svg_path.write_text(svg_content, encoding="utf-8")
    print(f"Generated SVG vector diagram at: {svg_path}")

    png_path = docs_dir / "dfa_diagram.png"
    generate_png_with_pillow(png_path)


if __name__ == "__main__":
    main()
