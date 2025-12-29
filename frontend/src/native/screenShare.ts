import { registerPlugin } from '@capacitor/core'

type StartResult = { ok: boolean }

export const ScreenShare = registerPlugin<{
  start(): Promise<StartResult>
}>('ScreenShare')
