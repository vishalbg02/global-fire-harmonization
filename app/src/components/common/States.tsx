export function LoadingState({ what }: { what: string }) {
  return (
    <p className="state state-loading" role="status">
      {`Loading ${what}…`}
    </p>
  )
}

export function ErrorState({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <div className="state state-error" role="alert">
      <p>{message}</p>
      <button type="button" onClick={onRetry}>
        Retry
      </button>
    </div>
  )
}

export function EmptyState({ message }: { message: string }) {
  return <p className="state state-empty">{message}</p>
}
