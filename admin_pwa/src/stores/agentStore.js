import { create } from 'zustand'
import { io } from 'socket.io-client'
import axios from 'axios'

// Production: Use Render URL, Development: Use proxy
const API_BASE = import.meta.env.VITE_API_URL || ''
const API_URL = `${API_BASE}/api`
const SOCKET_URL = API_BASE || window.location.origin

export const useAgentStore = create((set, get) => ({
    // State
    agents: [],
    selectedAgent: null,
    commandLogs: [],
    isLoading: false,
    error: null,
    socket: null,
    commandProgress: {},
    commandResults: {},  // Store command results by command_id
    lastResult: null,    // Store most recent result for quick access

    // Socket connection
    connectSocket: () => {
        // Don't reconnect if already connected
        const existingSocket = get().socket
        if (existingSocket?.connected) return

        console.log('Connecting to socket:', SOCKET_URL)

        const socket = io(SOCKET_URL, {
            path: '/socket.io',
            transports: ['websocket', 'polling'],
            reconnectionAttempts: 10,
            reconnectionDelay: 2000,
            reconnectionDelayMax: 10000,
            timeout: 10000
        })

        socket.on('connect', () => {
            console.log('Admin connected to server')
            set({ error: null })
        })

        socket.on('connect_error', (err) => {
            console.warn('Server connection unavailable:', err.message)
            set({ error: 'Server unavailable - ensure cloud_server is running on port 8000' })
        })

        socket.on('command_progress', (data) => {
            console.log('Progress received:', data)
            set((state) => ({
                commandProgress: {
                    ...state.commandProgress,
                    [data.command_id]: [...(state.commandProgress[data.command_id] || []), data]
                }
            }))
        })

        socket.on('command_result', (data) => {
            console.log('📊 Command result received:', data)
            console.log('📊 Result data content:', JSON.stringify(data.data, null, 2))

            // Store the full result with command_id as key
            set((state) => ({
                commandResults: {
                    ...state.commandResults,
                    [data.command_id]: {
                        ...data,
                        receivedAt: new Date().toISOString()
                    }
                },
                // Also store as lastResult for easy access
                lastResult: {
                    command_id: data.command_id,
                    agent_id: data.agent_id,
                    success: data.success,
                    data: data.data,
                    timestamp: data.timestamp
                }
            }))

            // Refresh agent list
            get().fetchAgents()
        })

        socket.on('disconnect', () => {
            console.log('Admin disconnected')
        })

        set({ socket })
    },

    disconnectSocket: () => {
        const { socket } = get()
        if (socket) {
            socket.disconnect()
            set({ socket: null })
        }
    },

    // Fetch all agents
    fetchAgents: async () => {
        set({ isLoading: true, error: null })

        try {
            const response = await axios.get(`${API_URL}/agents`)
            set({ agents: response.data, isLoading: false })
        } catch (error) {
            set({
                error: error.response?.data?.detail || 'Failed to fetch agents',
                isLoading: false
            })
        }
    },

    // Fetch single agent
    fetchAgent: async (agentId) => {
        set({ isLoading: true, error: null })

        try {
            const response = await axios.get(`${API_URL}/agents/${agentId}`)
            set({ selectedAgent: response.data, isLoading: false })
            return response.data
        } catch (error) {
            set({
                error: error.response?.data?.detail || 'Failed to fetch agent',
                isLoading: false
            })
            return null
        }
    },

    // Fetch agent logs
    fetchAgentLogs: async (agentId) => {
        try {
            const response = await axios.get(`${API_URL}/logs/${agentId}`)
            set({ commandLogs: response.data.logs })
            return response.data.logs
        } catch {
            return []
        }
    },

    // Send command to agent
    sendCommand: async (agentId, commandType, params = {}) => {
        try {
            const response = await axios.post(`${API_URL}/command`, {
                agent_id: agentId,
                command_type: commandType,
                params
            })

            // Initialize progress tracking
            set((state) => ({
                commandProgress: {
                    ...state.commandProgress,
                    [response.data.command_id]: []
                }
            }))

            return response.data
        } catch (error) {
            throw new Error(error.response?.data?.detail || 'Failed to send command')
        }
    },

    // Quick actions
    fullOptimize: async (agentId) => {
        return get().sendCommand(agentId, 'full_optimize')
    },

    healthCheck: async (agentId) => {
        return get().sendCommand(agentId, 'health_check')
    },

    deepClean: async (agentId) => {
        return get().sendCommand(agentId, 'deep_clean')
    },

    sysFix: async (agentId) => {
        return get().sendCommand(agentId, 'sys_fix')
    },

    uninstallAgent: async (agentId) => {
        return get().sendCommand(agentId, 'self_destruct', { confirm: true })
    },

    // Clear selection
    clearSelection: () => {
        set({ selectedAgent: null, commandLogs: [] })
    }
}))
