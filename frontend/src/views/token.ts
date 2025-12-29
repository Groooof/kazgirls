import { Preferences } from '@capacitor/preferences'

const KEY = 'access_token'

export async function setToken(token: string) {
  await Preferences.set({ key: KEY, value: token })
}
export async function getToken() {
  const { value } = await Preferences.get({ key: KEY })
  return value ?? null
}