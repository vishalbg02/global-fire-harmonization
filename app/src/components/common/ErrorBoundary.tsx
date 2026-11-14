import { Component } from 'react'
import type { ErrorInfo, ReactNode } from 'react'

interface Props {
  /** Shown instead of the children if one of them throws while rendering. */
  fallback: ReactNode
  children: ReactNode
}

interface State {
  failed: boolean
}

/** Keeps one failing view from blanking the whole page. */
export class ErrorBoundary extends Component<Props, State> {
  state: State = { failed: false }

  static getDerivedStateFromError(): State {
    return { failed: true }
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    console.error('A view failed to render:', error, info.componentStack)
  }

  render(): ReactNode {
    return this.state.failed ? this.props.fallback : this.props.children
  }
}
