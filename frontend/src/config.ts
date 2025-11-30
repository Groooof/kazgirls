interface Config {
  url: string,
  apiUrl: string
}

const isProd = false

export const config: Config = {
  url: isProd ? '/' : 'http://localhost:8000',
  apiUrl: '/api/v1',
}
