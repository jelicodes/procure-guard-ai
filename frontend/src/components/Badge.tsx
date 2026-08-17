import { HTMLAttributes, forwardRef } from "react";
import { cn } from "../utils";

export interface BadgeProps extends HTMLAttributes<HTMLDivElement> {
  variant?: "default" | "warning" | "destructive" | "success" | "outline";
}

const Badge = forwardRef<HTMLDivElement, BadgeProps>(
  ({ className, variant = "default", ...props }, ref) => {
    return (
      <div
        ref={ref}
        className={cn(
          "inline-flex items-center px-2.5 py-0.5 text-xs font-bold uppercase tracking-wider border-2 border-black whitespace-nowrap",
          {
            "bg-blue-400 text-black": variant === "default",
            "bg-yellow-400 text-black": variant === "warning",
            "bg-red-500 text-white": variant === "destructive",
            "bg-green-400 text-black": variant === "success",
            "bg-white text-black": variant === "outline",
          },
          className
        )}
        {...props}
      />
    );
  }
);
Badge.displayName = "Badge";

export { Badge };
