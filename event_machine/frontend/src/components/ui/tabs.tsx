import * as React from "react"
import * as TabsPrimitive from "@radix-ui/react-tabs"
import { cn } from "@/lib/utils"
const Tabs = TabsPrimitive.Root
const TabsList = React.forwardRef<React.ElementRef<typeof TabsPrimitive.List>, React.ComponentPropsWithoutRef<typeof TabsPrimitive.List>>(({ className, ...props }, ref) =>
  <TabsPrimitive.List ref={ref} className={cn("inline-flex h-10 items-center rounded-md bg-[#efeee9] p-1 text-[#6a6a65]", className)} {...props} />)
TabsList.displayName = "TabsList"
const TabsTrigger = React.forwardRef<React.ElementRef<typeof TabsPrimitive.Trigger>, React.ComponentPropsWithoutRef<typeof TabsPrimitive.Trigger>>(({ className, ...props }, ref) =>
  <TabsPrimitive.Trigger ref={ref} className={cn("inline-flex h-8 items-center justify-center whitespace-nowrap rounded-sm px-3 text-sm font-medium focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#343434] data-[state=active]:bg-white data-[state=active]:text-[#343434] data-[state=active]:shadow-sm", className)} {...props} />)
TabsTrigger.displayName = "TabsTrigger"
const TabsContent = React.forwardRef<React.ElementRef<typeof TabsPrimitive.Content>, React.ComponentPropsWithoutRef<typeof TabsPrimitive.Content>>(({ className, ...props }, ref) =>
  <TabsPrimitive.Content ref={ref} className={cn("mt-4 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#343434]", className)} {...props} />)
TabsContent.displayName = "TabsContent"
export { Tabs, TabsList, TabsTrigger, TabsContent }
