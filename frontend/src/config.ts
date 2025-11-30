interface Config {
  apiUrl: string
}

export const config: Config = {
  apiUrl: import.meta.env.VITE_API_URL || '/api/v1',
}
