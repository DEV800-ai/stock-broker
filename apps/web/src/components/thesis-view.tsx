import { Badge } from "@/components/ui/badge";
import type { badgeVariants } from "@/components/ui/badge";
import type { StockThesis } from "@/types";
import type { VariantProps } from "class-variance-authority";

type BadgeVariant = VariantProps<typeof badgeVariants>["variant"];

const CONFIDENCE_VARIANTS: Record<string, BadgeVariant> = {
  high: "success",
  medium: "warning",
  low: "outline",
};

export function ThesisView({ thesis }: { thesis: StockThesis }) {
  return (
    <>
      <div className="flex flex-col gap-2">
        <div className="flex items-center gap-3">
          <h2 className="font-mono text-lg font-medium leading-none">{thesis.ticker}</h2>
          {thesis.confidence && (
            <Badge variant={CONFIDENCE_VARIANTS[thesis.confidence] ?? "outline"}>
              {thesis.confidence.toUpperCase()} CONFIDENCE
            </Badge>
          )}
        </div>
        <p className="font-mono text-xs text-muted-foreground">
          Generated {new Date(thesis.generated_at).toLocaleString()} · {thesis.model}
        </p>
      </div>

      <div className="space-y-4 mt-4">
        <Section title="Why Interesting" content={thesis.why_interesting} />
        <Section title="Risk Factors" content={thesis.risk_factors} />
        {thesis.sector_context && <Section title="Sector Context" content={thesis.sector_context} />}
        {thesis.news_summary && <Section title="News Summary" content={thesis.news_summary} />}
        {thesis.catalysts && <Section title="Catalysts" content={thesis.catalysts} />}
        {thesis.peer_comparison && <Section title="Peer Comparison" content={thesis.peer_comparison} />}
      </div>
    </>
  );
}

function Section({ title, content }: { title: string; content: string }) {
  return (
    <div>
      <h3 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-1">{title}</h3>
      <p className="text-sm leading-relaxed text-foreground">{content}</p>
    </div>
  );
}
