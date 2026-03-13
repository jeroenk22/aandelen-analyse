import { useState, useEffect, useRef } from "react";

// Tooltip die verschijnt bij hover (desktop) of tap (mobiel) op indicator-labels
// direction: "up" | "down" | "right"
// align: "left" | "right" — horizontale uitlijning t.o.v. trigger
export default function IndicatorTooltip({ tooltip, children, direction = "up", align = "left" }) {
  const [show, setShow] = useState(false);
  const ref = useRef(null);

  // Sluit tooltip bij klik buiten (mobiel)
  useEffect(() => {
    if (!show) return;
    const handler = (e) => { if (ref.current && !ref.current.contains(e.target)) setShow(false); };
    document.addEventListener("mousedown", handler);
    document.addEventListener("touchstart", handler);
    return () => { document.removeEventListener("mousedown", handler); document.removeEventListener("touchstart", handler); };
  }, [show]);

  const vertPos = direction === "down" ? { top: "calc(100% + 8px)" } : { bottom: "calc(100% + 8px)" };
  // Kies uitlijning op basis van positie in viewport: voorkom dat tooltip rechts afvalt
  const triggerLeft = ref.current ? ref.current.getBoundingClientRect().left : 0;
  const flipRight = align !== "right" && triggerLeft > window.innerWidth / 2;
  const horizPos = (align === "right" || flipRight) ? { right: 0 } : { left: 0 };

  const handleClick = (e) => { e.stopPropagation(); setShow(v => !v); };

  return (
    <span ref={ref} style={{ position: "relative" }}
      onMouseEnter={() => setShow(true)}
      onMouseLeave={() => setShow(false)}
      onClick={handleClick}
    >
      {children}
      {show && tooltip && (
        <div style={{
          position: "absolute", ...vertPos, ...horizPos,
          background: "#0D1A2D", border: "1px solid #1E3A5F", borderRadius: 8,
          padding: "10px 14px", fontSize: 11, color: "#94A3B8",
          width: 280, maxWidth: "calc(100vw - 28px)", lineHeight: 1.65, zIndex: 200,
          pointerEvents: "none", boxShadow: "0 8px 32px rgba(0,0,0,0.6)",
          whiteSpace: "normal",
        }}>
          {tooltip}
        </div>
      )}
    </span>
  );
}
