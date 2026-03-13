import { useState } from "react";

// Tooltip die verschijnt bij hover op indicator-labels
export default function IndicatorTooltip({ tooltip, children, direction = "up" }) {
  const [show, setShow] = useState(false);
  const pos = direction === "down"
    ? { top: "calc(100% + 8px)", right: 0 }
    : { bottom: "calc(100% + 8px)", left: 0 };

  return (
    <span style={{ position: "relative" }}
      onMouseEnter={() => setShow(true)} onMouseLeave={() => setShow(false)}>
      {children}
      {show && tooltip && (
        <div style={{
          position: "absolute", ...pos,
          background: "#0D1A2D", border: "1px solid #1E3A5F", borderRadius: 8,
          padding: "10px 14px", fontSize: 11, color: "#94A3B8",
          width: 280, lineHeight: 1.65, zIndex: 200,
          pointerEvents: "none", boxShadow: "0 8px 32px rgba(0,0,0,0.6)",
          whiteSpace: "normal",
        }}>
          {tooltip}
        </div>
      )}
    </span>
  );
}
