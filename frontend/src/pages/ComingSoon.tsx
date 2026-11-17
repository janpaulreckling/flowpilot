import { Construction } from 'lucide-react'
import { Link } from 'react-router'

export function ComingSoon({ title, phase }: { title: string; phase: string }) {
  return (
    <div className="space-y-6">
      <h1 className="font-serif text-3xl font-semibold tracking-tight">{title}</h1>
      <div className="flex flex-col items-start gap-2 rounded-lg border border-dashed border-border px-6 py-8">
        <Construction className="size-5 text-muted-foreground" aria-hidden />
        <p className="font-medium">Not built yet</p>
        <p className="max-w-prose text-sm text-muted-foreground">
          This page arrives in {phase}. The design prototype covers the{' '}
          <Link to="/" className="text-evidence underline underline-offset-2">
            Decision Center
          </Link>{' '}
          and{' '}
          <Link to="/investigations/A-0142" className="text-evidence underline underline-offset-2">
            one investigation report
          </Link>
          .
        </p>
      </div>
    </div>
  )
}
