interface Config {
  apiUrl: string
  sentryDsn?: string
}

export const config: Config = {
  apiUrl: import.meta.env.VITE_API_URL || '/api/v1',
  sentryDsn: import.meta.env.VITE_SENTRY_DSN || undefined,
}
