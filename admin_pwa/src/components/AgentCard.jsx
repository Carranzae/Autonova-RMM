import { Link } from 'react-router-dom'

export default function AgentCard({ agent }) {
    const isOnline = agent.status === 'online'

    return (
        <Link
            to={`/agent/${agent.agent_id}`}
            className="glass rounded-xl p-5 hover:bg-white/10 transition-all duration-200 block group"
        >
            <div className="flex items-start justify-between mb-4">
                <div className="flex items-center gap-3">
                    {/* Computer Icon */}
                    <div className="w-12 h-12 bg-gradient-to-br from-primary-500/20 to-emerald-500/20 rounded-xl flex items-center justify-center">
                        <svg className="w-6 h-6 text-primary-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                        </svg>
                    </div>
                    <div>
                        <h3 className="font-semibold group-hover:text-primary-400 transition-colors">
                            {agent.hostname || 'Dispositivo Desconocido'}
                        </h3>
                        <p className="text-sm text-gray-500">{agent.username || 'Usuario'}</p>
                    </div>
                </div>

                {/* Status Badge */}
                <div className={`flex items-center gap-2 px-2 py-1 rounded-full text-xs font-medium ${isOnline
                        ? 'bg-emerald-500/20 text-emerald-400'
                        : 'bg-gray-500/20 text-gray-400'
                    }`}>
                    <span className={`w-2 h-2 rounded-full ${isOnline ? 'bg-emerald-400 animate-pulse' : 'bg-gray-400'}`}></span>
                    {isOnline ? 'En Línea' : 'Desconectado'}
                </div>
            </div>

            {/* Quick Info */}
            <div className="grid grid-cols-2 gap-3 text-sm">
                <div className="bg-dark-800/50 rounded-lg p-2">
                    <p className="text-gray-500 text-xs">ID Agente</p>
                    <p className="font-mono text-xs truncate">{agent.agent_id}</p>
                </div>
                <div className="bg-dark-800/50 rounded-lg p-2">
                    <p className="text-gray-500 text-xs">Último Heartbeat</p>
                    <p className="text-xs">{formatTimeAgo(agent.last_heartbeat)}</p>
                </div>
            </div>

            {/* Action Hint */}
            <div className="mt-4 pt-3 border-t border-white/5 flex items-center justify-between text-sm">
                <span className="text-gray-500">Clic para gestionar</span>
                <svg className="w-4 h-4 text-gray-500 group-hover:text-primary-400 group-hover:translate-x-1 transition-all" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                </svg>
            </div>
        </Link>
    )
}

function formatTimeAgo(isoString) {
    if (!isoString) return 'Nunca'

    const date = new Date(isoString)
    const now = new Date()
    const seconds = Math.floor((now - date) / 1000)

    if (seconds < 60) return 'Hace un momento'
    if (seconds < 3600) return `Hace ${Math.floor(seconds / 60)} min`
    if (seconds < 86400) return `Hace ${Math.floor(seconds / 3600)} h`
    return date.toLocaleDateString('es-ES')
}
