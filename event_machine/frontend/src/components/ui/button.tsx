import * as React from "react"
import { Slot } from "@radix-ui/react-slot"
import { cva, type VariantProps } from "class-variance-authority"
import { cn } from "@/lib/utils"

const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-md text-sm font-semibold transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#343434] focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-45 [&_svg]:pointer-events-none [&_svg]:size-4",
  { variants: {
    variant: {
      default: "bg-[#343434] text-[#F8F6F2] hover:bg-[#4a4a4a]",
      signal: "bg-[#EDF993] text-[#343434] hover:bg-[#dce879]",
      secondary: "bg-[#eeece7] text-[#343434] hover:bg-[#e4e2dc]",
      outline: "border border-[#c9c9c3] bg-white text-[#343434] hover:bg-[#F8F6F2]",
      ghost: "text-[#343434] hover:bg-[#eceae4]",
      link: "text-[#343434] underline-offset-4 hover:underline",
    },
    size: { default: "h-10 px-4 py-2", sm: "h-9 px-3", lg: "h-11 px-6", icon: "h-10 w-10" },
  }, defaultVariants: { variant: "default", size: "default" } }
)

type ButtonProps = React.ButtonHTMLAttributes<HTMLButtonElement> & VariantProps<typeof buttonVariants> & { asChild?: boolean }
const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(({ className, variant, size, asChild = false, ...props }, ref) => {
  const Component = asChild ? Slot : "button"
  return <Component className={cn(buttonVariants({ variant, size, className }))} ref={ref} {...props} />
})
Button.displayName = "Button"

export { Button, buttonVariants }
