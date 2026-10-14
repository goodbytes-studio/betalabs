import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"
import { cn } from "@/lib/utils"

const badgeVariants = cva("inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold tracking-tight", {
  variants: { variant: {
    default: "border-transparent bg-[#343434] text-white",
    signal: "border-transparent bg-[#EDF993] text-[#343434]",
    outline: "border-[#d9d7d0] bg-white text-[#54544e]",
    muted: "border-transparent bg-[#efeee9] text-[#676761]",
    danger: "border-transparent bg-[#f5e7e3] text-[#8b483e]",
  } }, defaultVariants: { variant: "default" }
})
type BadgeProps = React.HTMLAttributes<HTMLDivElement> & VariantProps<typeof badgeVariants>
function Badge({ className, variant, ...props }: BadgeProps) { return <div className={cn(badgeVariants({ variant }), className)} {...props} /> }
export { Badge, badgeVariants }
