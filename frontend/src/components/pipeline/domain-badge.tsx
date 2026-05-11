import { cn } from "@/lib/utils";

// ─── Domain emoji map ─────────────────────────────────────────────────────────

const DOMAIN_EMOJI: Record<string, string> = {
  healthcare: "🏥",
  finance: "💰",
  ecommerce: "🛒",
  hr: "👥",
  manufacturing: "⚙️",
  marketing: "📊",
  generic: "📋",
};

function getDomainEmoji(domain: string): string {
  return DOMAIN_EMOJI[domain.toLowerCase()] ?? "📋";
}

// ─── Props ────────────────────────────────────────────────────────────────────

interface DomainBadgeProps {
  domain: string;
  confidence?: number;
  size?: "sm" | "md";
  className?: string;
}

// ─── Component ────────────────────────────────────────────────────────────────

export function DomainBadge({
  domain,
  confidence,
  size = "md",
  className,
}: DomainBadgeProps) {
  const emoji = getDomainEmoji(domain);
  const displayName =
    domain.charAt(0).toUpperCase() + domain.slice(1).toLowerCase();

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full glass border border-white/10",
        size === "sm" && "px-2 py-0.5 text-xs",
        size === "md" && "px-3 py-1 text-sm",
        className,
      )}
    >
      <span role="img" aria-label={displayName}>
        {emoji}
      </span>
      <span className="font-medium text-foreground">{displayName}</span>
      {confidence !== undefined && (
        <span className="text-muted-foreground font-mono text-[10px]">
          {Math.round(confidence * 100)}%
        </span>
      )}
    </span>
  );
}
