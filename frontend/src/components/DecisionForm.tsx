import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useState, type FormEvent } from 'react'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { api, DEMO, type Decision } from '@/lib/api'

type Outcome = Decision['outcome']

const OUTCOMES: { value: Outcome; label: string }[] = [
  { value: 'approved', label: 'Approve' },
  { value: 'rejected', label: 'Reject' },
  { value: 'more_evidence', label: 'Need more evidence' },
]

export function DecisionForm({ subjectType, subjectId }: { subjectType: Decision['subject_type']; subjectId: string }) {
  const qc = useQueryClient()
  const [outcome, setOutcome] = useState<Outcome | null>(null)
  const [note, setNote] = useState('')
  const [error, setError] = useState<string | null>(null)
  const mutation = useMutation({
    mutationFn: () => api.decide({ subject_type: subjectType, subject_id: subjectId, outcome: outcome!, note }),
    onSuccess: () => {
      setNote('')
      setOutcome(null)
      void qc.invalidateQueries({ queryKey: ['decisions'] })
      void qc.invalidateQueries({ queryKey: ['alerts'] })
    },
    onError: (e: Error) => setError(e.message),
  })

  function submit(e: FormEvent) {
    e.preventDefault()
    if (!outcome) return setError('Choose an outcome.')
    if (!note.trim()) return setError('A note is required so the decision can be understood later.')
    setError(null)
    mutation.mutate()
  }

  return (
    <form onSubmit={submit} className="space-y-3" aria-label="Decision">
      <div role="radiogroup" aria-label="Outcome" className="flex flex-wrap gap-2">
        {OUTCOMES.map((o) => (
          <Button
            key={o.value}
            type="button"
            role="radio"
            aria-checked={outcome === o.value}
            variant={outcome === o.value ? 'default' : 'outline'}
            size="sm"
            onClick={() => setOutcome(o.value)}
          >
            {o.label}
          </Button>
        ))}
      </div>
      <label className="block space-y-1.5">
        <span className="text-sm font-medium">Note</span>
        <Textarea
          value={note}
          onChange={(e) => setNote(e.target.value)}
          placeholder="Why you decided this way, and anything to watch."
          rows={3}
        />
      </label>
      {error && (
        <p role="alert" className="text-sm text-destructive">
          {error}
        </p>
      )}
      {mutation.isSuccess && (
        <p role="status" className="text-sm text-muted-foreground">
          Decision {mutation.data.decision_id} recorded.
        </p>
      )}
      {DEMO && <p className="text-sm text-muted-foreground">Static demo: decisions are not saved here.</p>}
      <Button type="submit" disabled={mutation.isPending || DEMO}>
        {mutation.isPending ? 'Recording…' : 'Record decision'}
      </Button>
    </form>
  )
}
