import io from 'socket.io-client'
import { apiWebSockets } from '@/shared/constants'

export const socket = io(`${window.location.protocol}//${window.location.host}/userspace`,
  {
    path: apiWebSockets,
    transports: ['websocket'],
    rememberUpgrade: true,
    autoConnect: true,
    reconnection: true,
    reconnectionAttempts: Infinity,
    reconnectionDelay: 1000,
    reconnectionDelayMax: 2000,
    randomizationFactor: 0.5,
    timeout: 3000,
    auth: {
      jwt: ''
    }
  })
