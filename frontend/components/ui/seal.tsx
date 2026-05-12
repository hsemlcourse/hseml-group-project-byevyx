import { cn } from "@/lib/utils";

interface SealProps {
  size?: number;
  className?: string;
  /** Single kanji to render in the centre. */
  glyph?: string;
}

/**
 * Refined hanko-style seal — soft gradient instead of harsh red disc,
 * thin gold ring, gentle halo (not a pulse). Used as logo/decoration.
 */
export const Seal = ({ size = 40, className, glyph = "株" }: SealProps) => (
  <div
    className={cn(
      "stamp animate-seal-halo select-none ring-1 ring-gold/30",
      className,
    )}
    style={{
      width: size,
      height: size,
      fontSize: size * 0.52,
      lineHeight: 1,
    }}
    aria-hidden
  >
    <span className="-translate-y-[1px]">{glyph}</span>
  </div>
);
