import { useEffect } from 'react'
import { Link } from 'react-router-dom'
import { useAgentStore } from '../stores/agentStore'
import AgentCard from '../components/AgentCard'

export default function Dashboard() {
    const { agents, isLoading, error, fetchAgents } = useAgentStore()

    useEffect(() => {
        fetchAgents()
        const interval = setInterval(fetchAgents, 10000) // Actualizar cada 10s
        return () => clearInterval(interval)
    }, [fetchAgents])

    const onlineAgents = agents.filter(a => a.status === 'online')
    const offlineAgents = agents.filter(a => a.status !== 'online')

    return (
        <div className="space-y-8 animate-fade-in">
            {/* Estadísticas */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                <StatCard
                    label="Total Agentes"
                    value={agents.length}
                    icon={
                        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                        </svg>
                    }
                />
                <StatCard
                    label="En Línea"
                    value={onlineAgents.length}
                    icon={
                        <svg className="w-5 h-5 text-emerald-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5.636 18.364a9 9 0 010-12.728m12.728 0a9 9 0 010 12.728m-9.9-2.829a5 5 0 010-7.07m7.072 0a5 5 0 010 7.07M13 12a1 1 0 11-2 0 1 1 0 012 0z" />
                        </svg>
                    }
                    highlight="emerald"
                />
                <StatCard
                    label="Desconectados"
                    value={offlineAgents.length}
                    icon={
                        <svg className="w-5 h-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M18.364 5.636a9 9 0 010 12.728m0 0l-2.829-2.829m2.829 2.829L21 21M15.536 8.464a5 5 0 010 7.072m0 0l-2.829-2.829m-4.243 2.829a4.978 4.978 0 01-1.414-2.83m-1.414 5.658a9 9 0 01-2.167-9.238m7.824 2.167a1 1 0 111.414 1.414m-1.414-1.414L3 3m8.293 8.293l1.414 1.414" />
                        </svg>
                    }
                />
                <StatCard
                    label="Comandos"
                    value="—"
                    icon={
                        <svg className="w-5 h-5 text-primary-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 9l3 3-3 3m5 0h3M5 20h14a2 2 0 002-2V6a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                        </svg>
                    }
                />
            </div>

            {/* Grid de Agentes */}
            <div>
                <h2 className="text-xl font-semibold mb-4">Dispositivos Conectados</h2>

                {isLoading && agents.length === 0 ? (
                    <div className="text-center py-12 text-gray-500">
                        <svg className="animate-spin h-8 w-8 mx-auto mb-4" viewBox="0 0 24 24">
                            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                        </svg>
                        Cargando agentes...
                    </div>
                ) : agents.length === 0 ? (
                    <div className="text-center py-12 glass rounded-2xl">
                        <svg className="w-16 h-16 mx-auto text-gray-600 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                        </svg>
                        <h3 className="text-lg font-medium text-gray-400">Sin agentes conectados</h3>
                        <p className="text-gray-600 mt-1">Instala el agente en las máquinas cliente para comenzar</p>
                    </div>
                ) : (
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                        {agents.map((agent) => (
                            <AgentCard key={agent.agent_id} agent={agent} />
                        ))}
                    </div>
                )}

                {error && (
                    <div className="mt-4 p-4 bg-red-500/10 border border-red-500/50 rounded-lg text-red-400">
                        {error}
                    </div>
                )}
            </div>
        </div>
    )
}

function StatCard({ label, value, icon, highlight }) {
    const bgColor = highlight === 'emerald'
        ? 'bg-emerald-500/10 border-emerald-500/30'
        : 'bg-white/5 border-white/10'

    return (
        <div className={`${bgColor} border rounded-xl p-4`}>
            <div className="flex items-center gap-3">
                <div className="p-2 bg-white/10 rounded-lg">
                    {icon}
                </div>
                <div>
                    <p className="text-2xl font-bold">{value}</p>
                    <p className="text-xs text-gray-500">{label}</p>
                </div>
            </div>
        </div>
    )
}
