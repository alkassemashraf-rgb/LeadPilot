interface OrbProps {
  size?: number;
  color?: "primary" | "secondary" | "mixed";
  top?: string;
  left?: string;
  right?: string;
  bottom?: string;
  opacity?: number;
  blur?: number;
  drift?: boolean;
  className?: string;
}

export default function FloatingOrb({
  size = 400,
  color = "primary",
  top,
  left,
  right,
  bottom,
  opacity = 0.25,
  blur = 80,
  drift = true,
  className = "",
}: OrbProps) {
  const gradient = {
    primary: "radial-gradient(circle, rgba(15,118,110,1) 0%, transparent 70%)",
    secondary: "radial-gradient(circle, rgba(20,184,166,1) 0%, transparent 70%)",
    mixed: "radial-gradient(circle, rgba(15,118,110,0.8) 0%, rgba(20,184,166,0.4) 50%, transparent 70%)",
  }[color];

  return (
    <div
      aria-hidden="true"
      className={`absolute pointer-events-none ${drift ? "mk-drift" : ""} ${className}`}
      style={{
        width: size,
        height: size,
        top,
        left,
        right,
        bottom,
        background: gradient,
        opacity,
        filter: `blur(${blur}px)`,
        borderRadius: "50%",
        transform: "translate(-50%, -50%)",
      }}
    />
  );
}
