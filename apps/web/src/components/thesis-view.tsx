"use client";

import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import type { badgeVariants } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";
import type { StockThesis } from "@/types";
import type { ThesisTranslation } from "@/types";
import type { VariantProps } from "class-variance-authority";

type BadgeVariant = VariantProps<typeof badgeVariants>["variant"];

const CONFIDENCE_VARIANTS: Record<string, BadgeVariant> = {
  high: "success",
  medium: "warning",
  low: "outline",
};

export function ThesisView({ thesis }: { thesis: StockThesis }) {
  const [language, setLanguage] = useState<"en" | "he">("en");
  const [translation, setTranslation] = useState<ThesisTranslation | null>(null);
  const [loadingTranslation, setLoadingTranslation] = useState(false);
  const [translationError, setTranslationError] = useState<string | null>(null);

  async function showHebrew() {
    setLanguage("he");
    if (translation || loadingTranslation) return;
    setLoadingTranslation(true);
    setTranslationError(null);
    try {
      setTranslation(await api.thesisHebrew(thesis.id));
    } catch (err) {
      setTranslationError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoadingTranslation(false);
    }
  }

  const view = language === "he" && translation ? translation : thesis;
  const dir = language === "he" ? "rtl" : "ltr";

  return (
    <>
      <div className="flex flex-col gap-2">
        <div className="flex flex-wrap items-center gap-3">
          <h2 className="font-mono text-lg font-medium leading-none">{thesis.ticker}</h2>
          {thesis.confidence && (
            <Badge variant={CONFIDENCE_VARIANTS[thesis.confidence] ?? "outline"}>
              {thesis.confidence.toUpperCase()} CONFIDENCE
            </Badge>
          )}
          <div className="ml-auto flex rounded-md border border-border p-0.5">
            <Button size="sm" variant={language === "en" ? "secondary" : "ghost"} onClick={() => setLanguage("en")}>
              EN
            </Button>
            <Button size="sm" variant={language === "he" ? "secondary" : "ghost"} onClick={showHebrew}>
              HE
            </Button>
          </div>
        </div>
        <p className="font-mono text-xs text-muted-foreground">
          Generated {new Date(thesis.generated_at).toLocaleString()} · {thesis.model}
        </p>
      </div>

      <div className="space-y-4 mt-4" dir={dir}>
        {loadingTranslation && language === "he" ? (
          <p className="text-sm text-muted-foreground">מתרגם לעברית...</p>
        ) : translationError && language === "he" ? (
          <p className="text-sm text-destructive">{translationError}</p>
        ) : (
          <>
            <Section title={language === "he" ? "למה זה מעניין" : "Why Interesting"} content={view.why_interesting} />
            <Section title={language === "he" ? "גורמי סיכון" : "Risk Factors"} content={view.risk_factors} />
            {view.sector_context && (
              <Section title={language === "he" ? "הקשר סקטוריאלי" : "Sector Context"} content={view.sector_context} />
            )}
            {view.elliott_wave_context && (
              <Section title={language === "he" ? "הקשר גלי אליוט" : "Elliott Wave Context"} content={view.elliott_wave_context} />
            )}
            {view.news_summary && (
              <Section title={language === "he" ? "סיכום חדשות" : "News Summary"} content={view.news_summary} />
            )}
            {view.catalysts && <Section title={language === "he" ? "זרזים" : "Catalysts"} content={view.catalysts} />}
            {view.peer_comparison && (
              <Section title={language === "he" ? "השוואת עמיתים" : "Peer Comparison"} content={view.peer_comparison} />
            )}
          </>
        )}
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
