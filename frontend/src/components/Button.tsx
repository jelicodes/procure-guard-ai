import { ButtonHTMLAttributes, forwardRef } from "react";
import { cn } from "../utils";

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "danger" | "success" | "outline";
  size?: "sm" | "md" | "lg";
}

const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = "primary", size = "md", ...props }, ref) => {
    return (
      <button
        ref={ref}
        className={cn(
          "inline-flex items-center justify-center font-bold uppercase tracking-wider border-2 border-black transition-all",
          "focus:outline-none focus:ring-2 focus:ring-black focus:ring-offset-2",
          "active:translate-x-[2px] active:translate-y-[2px] active:shadow-none",
          {
            "bg-yellow-400 text-black shadow-[4px_4px_0_0_#000] hover:bg-yellow-300": variant === "primary",
            "bg-blue-400 text-black shadow-[4px_4px_0_0_#000] hover:bg-blue-300": variant === "secondary",
            "bg-red-500 text-white shadow-[4px_4px_0_0_#000] hover:bg-red-400": variant === "danger",
            "bg-green-400 text-black shadow-[4px_4px_0_0_#000] hover:bg-green-300": variant === "success",
            "bg-white text-black shadow-[4px_4px_0_0_#000] hover:bg-gray-50": variant === "outline",
            "px-3 py-1.5 text-sm": size === "sm",
            "px-5 py-2.5 text-base": size === "md",
            "px-8 py-4 text-lg": size === "lg",
          },
          className
        )}
        {...props}
      />
    );
  }
);
Button.displayName = "Button";

export { Button };
