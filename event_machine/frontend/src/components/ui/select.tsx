import * as React from "react"
import * as SelectPrimitive from "@radix-ui/react-select"
import { Check, ChevronDown, ChevronUp } from "lucide-react"
import { cn } from "@/lib/utils"

const Select = SelectPrimitive.Root
const SelectValue = SelectPrimitive.Value
const SelectTrigger = React.forwardRef<React.ElementRef<typeof SelectPrimitive.Trigger>, React.ComponentPropsWithoutRef<typeof SelectPrimitive.Trigger>>(({ className, children, ...props }, ref) =>
  <SelectPrimitive.Trigger ref={ref} className={cn("flex h-10 w-full items-center justify-between gap-2 rounded-md border border-[#cfcdc6] bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#343434] disabled:opacity-50 [&>span]:truncate", className)} {...props}>
    {children}<SelectPrimitive.Icon asChild><ChevronDown className="h-4 w-4 opacity-60" /></SelectPrimitive.Icon>
  </SelectPrimitive.Trigger>)
SelectTrigger.displayName = "SelectTrigger"
const SelectContent = React.forwardRef<React.ElementRef<typeof SelectPrimitive.Content>, React.ComponentPropsWithoutRef<typeof SelectPrimitive.Content>>(({ className, children, position = "popper", ...props }, ref) =>
  <SelectPrimitive.Portal><SelectPrimitive.Content ref={ref} position={position} className={cn("z-50 max-h-80 min-w-36 overflow-hidden rounded-md border border-[#d8d6d0] bg-white p-1 text-[#343434] shadow-lg", className)} {...props}>
    <SelectPrimitive.ScrollUpButton className="flex items-center justify-center p-1"><ChevronUp size={16} /></SelectPrimitive.ScrollUpButton>
    <SelectPrimitive.Viewport>{children}</SelectPrimitive.Viewport>
    <SelectPrimitive.ScrollDownButton className="flex items-center justify-center p-1"><ChevronDown size={16} /></SelectPrimitive.ScrollDownButton>
  </SelectPrimitive.Content></SelectPrimitive.Portal>)
SelectContent.displayName = "SelectContent"
const SelectItem = React.forwardRef<React.ElementRef<typeof SelectPrimitive.Item>, React.ComponentPropsWithoutRef<typeof SelectPrimitive.Item>>(({ className, children, ...props }, ref) =>
  <SelectPrimitive.Item ref={ref} className={cn("relative flex cursor-pointer select-none items-center rounded-sm py-2 pl-8 pr-2 text-sm outline-none focus:bg-[#f2f1ec] data-[disabled]:opacity-50", className)} {...props}>
    <span className="absolute left-2 flex h-4 w-4 items-center justify-center"><SelectPrimitive.ItemIndicator><Check size={15} /></SelectPrimitive.ItemIndicator></span>
    <SelectPrimitive.ItemText>{children}</SelectPrimitive.ItemText>
  </SelectPrimitive.Item>)
SelectItem.displayName = "SelectItem"
export { Select, SelectValue, SelectTrigger, SelectContent, SelectItem }
