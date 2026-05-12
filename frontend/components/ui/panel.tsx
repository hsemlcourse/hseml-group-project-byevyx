import { cn } from "@/lib/utils";

interface PanelProps extends React.HTMLAttributes<HTMLDivElement> {
  title?: string;
  kanji?: string;
  right?: React.ReactNode;
  /** Slightly bigger kanji watermark for heavier panels. */
  kanjiSize?: "sm" | "md" | "lg";
}

/**
 * Boxed surface with a soft gold-on-black title bar and a subtle kanji
 * watermark in the bottom-right corner.
 */
export const Panel = ({
  className,
  title,
  kanji,
  kanjiSize = "lg",
  right,
  children,
  ...rest
}: PanelProps) => (
  <section className={cn("panel", className)} {...rest}>
    {(title || right) && (
      <header className="panel-header">
        {title ? <span className="panel-title">{title}</span> : <span />}
        {right}
      </header>
    )}
    <div className="relative">
      {kanji && (
        <span
          className={cn(
            "kanji-watermark right-4 bottom-2",
            kanjiSize === "sm" && "text-[4rem]",
            kanjiSize === "md" && "text-[6rem]",
            kanjiSize === "lg" && "text-[8rem]",
          )}
          aria-hidden
        >
          {kanji}
        </span>
      )}
      <div className="relative z-10">{children}</div>
    </div>
  </section>
);
