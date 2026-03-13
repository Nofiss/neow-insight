import * as React from 'react'

import { cn } from '@/lib/utils'

function Alert({ className, ...props }: React.ComponentProps<'div'>) {
  return (
    <div
      role="alert"
      className={cn(
        'bg-card text-card-foreground rounded-xl border px-4 py-3 text-sm',
        className,
      )}
      {...props}
    />
  )
}

function AlertTitle({ className, ...props }: React.ComponentProps<'h5'>) {
  return <h5 className={cn('mb-1 font-semibold', className)} {...props} />
}

function AlertDescription({ className, ...props }: React.ComponentProps<'div'>) {
  return <div className={cn('text-muted-foreground text-sm', className)} {...props} />
}

export { Alert, AlertDescription, AlertTitle }
