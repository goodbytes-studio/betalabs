import * as React from "react"
import * as DialogPrimitive from "@radix-ui/react-dialog"
import { X } from "lucide-react"
import { cn } from "@/lib/utils"
const Dialog = DialogPrimitive.Root
const DialogTrigger = DialogPrimitive.Trigger
const DialogClose = DialogPrimitive.Close
const DialogPortal = DialogPrimitive.Portal
const DialogOverlay = React.forwardRef<React.ElementRef<typeof DialogPrimitive.Overlay>, React.ComponentPropsWithoutRef<typeof DialogPrimitive.Overlay>>(({ className, ...props }, ref) =>
  <DialogPrimitive.Overlay ref={ref} className={cn("fixed inset-0 z-50 bg-[#252525]/50 backdrop-blur-[2px] data-[state=open]:animate-in", className)} {...props} />)
DialogOverlay.displayName = "DialogOverlay"
const DialogContent = React.forwardRef<React.ElementRef<typeof DialogPrimitive.Content>, React.ComponentPropsWithoutRef<typeof DialogPrimitive.Content>>(({ className, children, ...props }, ref) =>
  <DialogPortal><DialogOverlay /><DialogPrimitive.Content ref={ref} className={cn("fixed left-1/2 top-1/2 z-50 grid max-h-[90vh] w-[calc(100%-2rem)] max-w-2xl -translate-x-1/2 -translate-y-1/2 gap-4 overflow-y-auto rounded-xl border border-[#e2e0da] bg-[#F8F6F2] p-6 shadow-xl focus:outline-none", className)} {...props}>
    {children}<DialogPrimitive.Close className="absolute right-4 top-4 rounded-sm p-1 text-[#696963] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#343434]"><X size={18} /><span className="sr-only">Fermer</span></DialogPrimitive.Close>
  </DialogPrimitive.Content></DialogPortal>)
DialogContent.displayName = "DialogContent"
const DialogHeader = ({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) => <div className={cn("space-y-1.5 text-left", className)} {...props} />
const DialogTitle = React.forwardRef<React.ElementRef<typeof DialogPrimitive.Title>, React.ComponentPropsWithoutRef<typeof DialogPrimitive.Title>>(({ className, ...props }, ref) =>
  <DialogPrimitive.Title ref={ref} className={cn("text-xl font-semibold tracking-tight", className)} {...props} />)
DialogTitle.displayName = "DialogTitle"
const DialogDescription = React.forwardRef<React.ElementRef<typeof DialogPrimitive.Description>, React.ComponentPropsWithoutRef<typeof DialogPrimitive.Description>>(({ className, ...props }, ref) =>
  <DialogPrimitive.Description ref={ref} className={cn("text-sm text-[#696963]", className)} {...props} />)
DialogDescription.displayName = "DialogDescription"
export { Dialog, DialogTrigger, DialogClose, DialogContent, DialogHeader, DialogTitle, DialogDescription }
