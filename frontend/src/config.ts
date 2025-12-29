interface Config {
  url: string,
  apiUrl: string
}

const isProd = true

export const config: Config = {
  url: isProd ? 'https://nex2ilo.com' : 'http://localhost:8000',
  apiUrl: '/api/v1',
}
