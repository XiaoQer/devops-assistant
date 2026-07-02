import { client } from './client'

export interface AiIntentResolution {
  intent: string
  confidence: number
  target: Record<string, unknown>
  requires_confirmation: boolean
  recommended_action: {
    type?: string
    route?: string
  }
  reasoning: string
  matched_application?: {
    id: number
    name: string
  } | null
  matched_environment?: string | null
  mock?: boolean
  text: string
}

export const aiApi = {
  resolveIntent: (text: string) =>
    client.post<never, AiIntentResolution>('/ai/intent/resolve', { text }),
}

