import { FlaskConical } from 'lucide-react'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'

/** Marks content that is a design prototype, not yet produced by the real backend. */
export function PrototypeNote({ children = 'Prototype · sample content' }: { children?: string }) {
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <span
          className="inline-flex items-center gap-1.5 rounded-full border border-dashed border-border px-2.5 py-0.5 text-xs text-muted-foreground"
          tabIndex={0}
        >
          <FlaskConical className="size-3.5" aria-hidden />
          {children}
        </span>
      </TooltipTrigger>
      <TooltipContent className="max-w-xs">
        Numbers were computed once from the synthetic dataset to judge the design. In the finished
        app they come from the metric layer and real investigation runs.
      </TooltipContent>
    </Tooltip>
  )
}
