import { useEffect, useState, useRef } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useAgentStore } from '../stores/agentStore'

// Traffic light colors
const STATUS_COLORS = {
    idle: 'bg-gray-500',
    running: 'bg-amber-500 animate-pulse',
    success: 'bg-emerald-500',
    error: 'bg-red-500'
}

export default function AgentDetail() {
    const { agentId } = useParams()
    const navigate = useNavigate()
    const consoleRef = useRef(null)
    const {
        selectedAgent,
        commandProgress,
        commandResults,
        fetchAgent,
        sendCommand,
        clearSelection
    } = useAgentStore()

    // Get socket for event subscription
    const { socket } = useAgentStore()

    const [commandStatuses, setCommandStatuses] = useState({})
    const [consoleLogs, setConsoleLogs] = useState([])
    const [isExecuting, setIsExecuting] = useState(false)
    const [currentCommandId, setCurrentCommandId] = useState(null)
    const [currentCommandType, setCurrentCommandType] = useState(null)

    useEffect(() => {
        fetchAgent(agentId)
        return () => clearSelection()
    }, [agentId, fetchAgent, clearSelection])

    // Watch commandResults for completion
    useEffect(() => {
        if (currentCommandId && commandResults[currentCommandId]) {
            const result = commandResults[currentCommandId]
            const success = result.success !== false

            console.log('Command completed via store:', result)

            if (currentCommandType) {
                setCommandStatuses(prev => ({
                    ...prev,
                    [currentCommandType]: success ? 'success' : 'error'
                }))

                const timestamp = new Date().toLocaleTimeString('es-ES')
                setConsoleLogs(prev => [...prev, {
                    timestamp,
                    message: success
                        ? `✅ Comando completado exitosamente`
                        : `❌ Comando falló: ${result.error || 'Error desconocido'}`,
                    type: success ? 'success' : 'error'
                }])

                setTimeout(() => {
                    setCommandStatuses(prev => ({ ...prev, [currentCommandType]: 'idle' }))
                }, 3000)
            }

            setIsExecuting(false)
            setCurrentCommandId(null)
            setCurrentCommandType(null)
        }
    }, [commandResults, currentCommandId, currentCommandType])

    // Subscribe to command completion events
    useEffect(() => {
        if (!socket) return

        const handleCommandResult = (data) => {
            console.log('Command result received:', data)

            // Match by command_id OR by agent_id if we're currently executing
            const isOurCommand = data.command_id === currentCommandId ||
                (isExecuting && data.agent_id === agentId)

            if (isOurCommand) {
                const success = data.success !== false

                // Update status based on result
                if (currentCommandType) {
                    setCommandStatuses(prev => ({
                        ...prev,
                        [currentCommandType]: success ? 'success' : 'error'
                    }))

                    // Add completion log
                    const timestamp = new Date().toLocaleTimeString('es-ES')
                    setConsoleLogs(prev => [...prev, {
                        timestamp,
                        message: success
                            ? `✅ Comando completado exitosamente`
                            : `❌ Comando falló: ${data.error || 'Error desconocido'}`,
                        type: success ? 'success' : 'error'
                    }])

                    // Reset after 3 seconds
                    setTimeout(() => {
                        setCommandStatuses(prev => ({ ...prev, [currentCommandType]: 'idle' }))
                    }, 3000)
                }

                // Reset execution state
                setIsExecuting(false)
                setCurrentCommandId(null)
                setCurrentCommandType(null)
            }
        }

        socket.on('command_result', handleCommandResult)

        return () => {
            socket.off('command_result', handleCommandResult)
        }
    }, [socket, currentCommandId, currentCommandType])

    // Subscribe to command progress updates
    useEffect(() => {
        if (currentCommandId && commandProgress[currentCommandId]) {
            const progressData = commandProgress[currentCommandId]
            progressData.forEach((progress, index) => {
                const message = progress.data?.message || JSON.stringify(progress.data)
                const level = progress.data?.level || 'info'
                // Only add if not already in logs (simple dedup)
                setConsoleLogs(prev => {
                    const exists = prev.some(log => log.message === message && log.progressIndex === index)
                    if (!exists) {
                        return [...prev, {
                            timestamp: new Date(progress.timestamp || Date.now()).toLocaleTimeString('es-ES'),
                            message,
                            type: level,
                            progressIndex: index
                        }]
                    }
                    return prev
                })
            })
        }
    }, [currentCommandId, commandProgress])

    // Auto-scroll console
    useEffect(() => {
        if (consoleRef.current) {
            consoleRef.current.scrollTop = consoleRef.current.scrollHeight
        }
    }, [consoleLogs])

    const addLog = (message, type = 'info') => {
        const timestamp = new Date().toLocaleTimeString('es-ES')
        setConsoleLogs(prev => [...prev, { timestamp, message, type }])
    }

    const executeCommand = async (commandType, label) => {
        if (!selectedAgent || selectedAgent.status !== 'online') {
            addLog(`Error: Agente no disponible`, 'error')
            return
        }

        setIsExecuting(true)
        setCurrentCommandType(commandType)  // Track which command type is running
        setCommandStatuses(prev => ({ ...prev, [commandType]: 'running' }))
        addLog(`Iniciando ${label}...`, 'info')

        try {
            const result = await sendCommand(agentId, commandType)
            // Track command ID for progress subscription
            if (result?.command_id) {
                setCurrentCommandId(result.command_id)
            }
            // Command completion is handled by command_result event listener

        } catch (error) {
            setCommandStatuses(prev => ({ ...prev, [commandType]: 'error' }))
            addLog(`✗ Error en ${label}: ${error.message}`, 'error')

            setTimeout(() => {
                setCommandStatuses(prev => ({ ...prev, [commandType]: 'idle' }))
            }, 3000)
            setIsExecuting(false)
        }
    }

    // Execute command with additional parameters
    const executeCommandWithParams = async (commandType, params, label) => {
        addLog(`Iniciando ${label}...`, 'info')
        setIsExecuting(true)
        setCommandStatuses(prev => ({ ...prev, [commandType]: 'running' }))
        setCurrentCommandType(commandType)

        try {
            const result = await sendCommand(agentId, commandType, params)
            if (result?.command_id) {
                setCurrentCommandId(result.command_id)
            }
            addLog(`Procesando ${label}...`, 'info')
        } catch (error) {
            setCommandStatuses(prev => ({ ...prev, [commandType]: 'error' }))
            addLog(`✗ Error en ${label}: ${error.message}`, 'error')

            setTimeout(() => {
                setCommandStatuses(prev => ({ ...prev, [commandType]: 'idle' }))
            }, 3000)
            setIsExecuting(false)
        }
    }

    const handleWorkComplete = async () => {
        if (!confirm('⚠️ ATENCIÓN: Esto desinstalará el agente del equipo del cliente.\n\n¿Confirmar TRABAJO TERMINADO?')) {
            return
        }

        addLog('Iniciando proceso de finalización...', 'warning')

        try {
            await sendCommand(agentId, 'self_destruct', { confirm: true })
            addLog('✓ Agente desinstalado correctamente', 'success')
            addLog('Redirigiendo al panel principal...', 'info')

            setTimeout(() => navigate('/'), 2000)
        } catch (error) {
            addLog(`✗ Error: ${error.message}`, 'error')
        }
    }

    // Report state
    const [lastReport, setLastReport] = useState(null)
    const [showReportModal, setShowReportModal] = useState(false)

    const handleGenerateReport = async () => {
        addLog('📄 Generando reporte profesional...', 'info')
        setCommandStatuses(prev => ({ ...prev, 'generate_report': 'running' }))
        setCurrentCommandType('generate_report')

        try {
            const result = await sendCommand(agentId, 'generate_report')
            if (result?.command_id) {
                setCurrentCommandId(result.command_id)
            }
            // Report will be received via command_result event
        } catch (error) {
            setCommandStatuses(prev => ({ ...prev, 'generate_report': 'error' }))
            addLog(`✗ Error generando reporte: ${error.message}`, 'error')
            setIsExecuting(false)
        }
    }

    // Subscribe to report results
    useEffect(() => {
        if (!socket) return

        const handleReportResult = (data) => {
            if (data.data?.html) {
                setLastReport({
                    html: data.data.html,
                    filename: data.data.filename || 'reporte.html',
                    timestamp: new Date().toISOString()
                })
                addLog('✅ Reporte listo - Haz clic en "Ver Reporte" para visualizar', 'success')
            }
        }

        socket.on('command_result', (data) => {
            if (data.data?.html) {
                handleReportResult(data)
            }
        })

        return () => { }
    }, [socket])

    const handleViewReport = () => {
        if (lastReport?.html) {
            setShowReportModal(true)
        } else {
            addLog('⚠️ Primero genera un reporte', 'warning')
        }
    }

    const handleDownloadReport = () => {
        if (!lastReport?.html) {
            addLog('⚠️ Primero genera un reporte', 'warning')
            return
        }

        // Create blob and download
        const blob = new Blob([lastReport.html], { type: 'text/html' })
        const url = URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = `reporte_${selectedAgent?.hostname || 'equipo'}_${new Date().toISOString().split('T')[0]}.html`
        document.body.appendChild(a)
        a.click()
        document.body.removeChild(a)
        URL.revokeObjectURL(url)

        addLog('📥 Reporte descargado exitosamente', 'success')
    }

    if (!selectedAgent) {
        return (
            <div className="flex items-center justify-center h-64">
                <div className="text-center">
                    <svg className="animate-spin h-8 w-8 mx-auto mb-4 text-primary-500" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                    </svg>
                    <p className="text-gray-400">Cargando información del agente...</p>
                </div>
            </div>
        )
    }

    const isOnline = selectedAgent.status === 'online'

    // Command Button Component
    const CommandButton = ({ id, label, icon, onClick, disabled, color = 'blue' }) => {
        const status = commandStatuses[id] || 'idle'
        const colorClasses = {
            blue: 'from-blue-600 to-blue-700 hover:from-blue-500 hover:to-blue-600 border-blue-500/30',
            orange: 'from-amber-600 to-amber-700 hover:from-amber-500 hover:to-amber-600 border-amber-500/30',
            green: 'from-emerald-600 to-emerald-700 hover:from-emerald-500 hover:to-emerald-600 border-emerald-500/30',
            red: 'from-red-600 to-red-700 hover:from-red-500 hover:to-red-600 border-red-500/30',
            gray: 'from-gray-600 to-gray-700 hover:from-gray-500 hover:to-gray-600 border-gray-500/30'
        }

        return (
            <button
                onClick={onClick}
                disabled={disabled || status === 'running'}
                className={`relative p-3 sm:p-4 rounded-xl text-center transition-all duration-200 
                    bg-gradient-to-br ${colorClasses[color]} border
                    disabled:opacity-50 disabled:cursor-not-allowed 
                    active:scale-95 shadow-lg hover:shadow-xl min-h-[80px] sm:min-h-[100px]`}
            >
                {/* Status indicator */}
                <div className={`absolute top-2 right-2 w-3 h-3 rounded-full ${STATUS_COLORS[status]}`} />

                <span className="text-xl sm:text-2xl block mb-1 sm:mb-2">{icon}</span>
                <span className="text-xs sm:text-sm font-medium block leading-tight">{label}</span>
            </button>
        )
    }

    return (
        <div className="space-y-6 animate-fade-in">
            {/* Header */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <div className="flex items-center gap-4">
                    <button
                        onClick={() => navigate('/')}
                        className="p-2 hover:bg-white/10 rounded-lg transition-colors"
                    >
                        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                        </svg>
                    </button>
                    <div>
                        <div className="flex items-center gap-3">
                            <h1 className="text-2xl font-bold">{selectedAgent.hostname || 'Dispositivo'}</h1>
                            <span className={`w-3 h-3 rounded-full ${isOnline ? 'bg-emerald-500 animate-pulse' : 'bg-gray-500'}`}></span>
                            <span className={`text-sm ${isOnline ? 'text-emerald-400' : 'text-gray-400'}`}>
                                {isOnline ? 'EN LÍNEA' : 'DESCONECTADO'}
                            </span>
                        </div>
                        <p className="text-gray-500">{selectedAgent.username} • {selectedAgent.agent_id}</p>
                    </div>
                </div>
            </div>

            {/* Command Sections Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 sm:gap-6">

                {/* Section 1: Diagnóstico (Blue) */}
                <div className="glass rounded-xl p-4 sm:p-5 border border-blue-500/20">
                    <h3 className="font-semibold mb-3 sm:mb-4 flex items-center gap-2 text-blue-400 text-sm sm:text-base">
                        <span className="w-2 h-2 sm:w-3 sm:h-3 rounded-full bg-blue-500"></span>
                        DIAGNÓSTICO
                    </h3>
                    <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 sm:gap-3">
                        <CommandButton
                            id="scan_pc"
                            label="Escanear PC"
                            icon="🔍"
                            color="blue"
                            onClick={() => executeCommand('health_check', 'Escaneo de PC')}
                            disabled={!isOnline || isExecuting}
                        />
                        <CommandButton
                            id="view_processes"
                            label="Ver Procesos"
                            icon="📊"
                            color="blue"
                            onClick={() => executeCommand('view_processes', 'Ver Procesos')}
                            disabled={!isOnline || isExecuting}
                        />
                        <CommandButton
                            id="analyze_disk"
                            label="Analizar Disco"
                            icon="💾"
                            color="blue"
                            onClick={() => executeCommand('analyze_disk', 'Análisis de Disco')}
                            disabled={!isOnline || isExecuting}
                        />
                    </div>
                </div>

                {/* Section 2: Limpieza Profunda (Orange) */}
                <div className="glass rounded-xl p-4 sm:p-5 border border-amber-500/20">
                    <h3 className="font-semibold mb-3 sm:mb-4 flex items-center gap-2 text-amber-400 text-sm sm:text-base">
                        <span className="w-2 h-2 sm:w-3 sm:h-3 rounded-full bg-amber-500"></span>
                        LIMPIEZA PROFUNDA
                    </h3>
                    <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 sm:gap-3">
                        <CommandButton
                            id="clear_cache"
                            label="Borrar Caché"
                            icon="🧹"
                            color="orange"
                            onClick={() => executeCommand('deep_clean', 'Limpieza de Caché')}
                            disabled={!isOnline || isExecuting}
                        />
                        <CommandButton
                            id="force_delete"
                            label="Fuerza Bruta"
                            icon="💪"
                            color="orange"
                            onClick={() => executeCommand('force_delete', 'Eliminación Forzada')}
                            disabled={!isOnline || isExecuting}
                        />
                        <CommandButton
                            id="clean_registry"
                            label="Limpiar Registro"
                            icon="📝"
                            color="orange"
                            onClick={() => executeCommand('clean_registry', 'Limpieza de Registro')}
                            disabled={!isOnline || isExecuting}
                        />
                    </div>
                </div>

                {/* Section 3: Reparación (Green) */}
                <div className="glass rounded-xl p-4 sm:p-5 border border-emerald-500/20">
                    <h3 className="font-semibold mb-3 sm:mb-4 flex items-center gap-2 text-emerald-400 text-sm sm:text-base">
                        <span className="w-2 h-2 sm:w-3 sm:h-3 rounded-full bg-emerald-500"></span>
                        REPARACIÓN
                    </h3>
                    <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 sm:gap-3">
                        <CommandButton
                            id="system_repair"
                            label="Reparar Sistema"
                            icon="🔧"
                            color="green"
                            onClick={() => executeCommand('sys_fix', 'Reparación de Sistema')}
                            disabled={!isOnline || isExecuting}
                        />
                        <CommandButton
                            id="speed_boot"
                            label="Acelerar Inicio"
                            icon="🚀"
                            color="green"
                            onClick={() => executeCommand('speed_up_boot', 'Optimización de Inicio')}
                            disabled={!isOnline || isExecuting}
                        />
                        <CommandButton
                            id="network_reset"
                            label="Reset de Red"
                            icon="🌐"
                            color="green"
                            onClick={() => executeCommand('network_reset', 'Reset de Red')}
                            disabled={!isOnline || isExecuting}
                        />
                    </div>
                </div>

                {/* Section 4: Control Avanzado (Purple) */}
                <div className="glass rounded-xl p-4 sm:p-5 border border-purple-500/20">
                    <h3 className="font-semibold mb-3 sm:mb-4 flex items-center gap-2 text-purple-400 text-sm sm:text-base">
                        <span className="w-2 h-2 sm:w-3 sm:h-3 rounded-full bg-purple-500"></span>
                        CONTROL AVANZADO
                    </h3>
                    <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 sm:gap-3">
                        <CommandButton
                            id="list_programs"
                            label="Ver Programas"
                            icon="📋"
                            color="gray"
                            onClick={() => executeCommand('list_programs', 'Listando Programas')}
                            disabled={!isOnline || isExecuting}
                        />
                        <button
                            onClick={() => {
                                const program = prompt('Nombre del programa a desinstalar:')
                                if (program) {
                                    executeCommandWithParams('force_uninstall', { program_name: program }, `Desinstalando ${program}`)
                                }
                            }}
                            disabled={!isOnline || isExecuting}
                            className="relative p-3 sm:p-4 rounded-xl text-center transition-all duration-200 
                                bg-gradient-to-br from-rose-600 to-rose-700 hover:from-rose-500 hover:to-rose-600 
                                border border-rose-500/30
                                disabled:opacity-50 disabled:cursor-not-allowed 
                                active:scale-95 shadow-lg min-h-[80px] sm:min-h-[100px]"
                        >
                            <span className="text-xl sm:text-2xl block mb-1 sm:mb-2">🗑️</span>
                            <span className="text-xs sm:text-sm font-medium block leading-tight">Desinstalar App</span>
                        </button>
                        <button
                            onClick={() => {
                                const process = prompt('Nombre del proceso a terminar (ej: chrome.exe):')
                                if (process) {
                                    executeCommandWithParams('kill_process', { process_name: process }, `Terminando ${process}`)
                                }
                            }}
                            disabled={!isOnline || isExecuting}
                            className="relative p-3 sm:p-4 rounded-xl text-center transition-all duration-200 
                                bg-gradient-to-br from-red-600 to-red-700 hover:from-red-500 hover:to-red-600 
                                border border-red-500/30
                                disabled:opacity-50 disabled:cursor-not-allowed 
                                active:scale-95 shadow-lg min-h-[80px] sm:min-h-[100px]"
                        >
                            <span className="text-xl sm:text-2xl block mb-1 sm:mb-2">🔪</span>
                            <span className="text-xs sm:text-sm font-medium block leading-tight">Terminar Proceso</span>
                        </button>
                    </div>
                </div>

                {/* Section 5: Finalización y Reportes */}
                <div className="glass rounded-xl p-4 sm:p-5 border border-gray-500/20">
                    <h3 className="font-semibold mb-3 sm:mb-4 flex items-center gap-2 text-gray-400 text-sm sm:text-base">
                        <span className="w-2 h-2 sm:w-3 sm:h-3 rounded-full bg-gray-500"></span>
                        REPORTES Y FINALIZACIÓN
                    </h3>
                    <div className="grid grid-cols-2 gap-2 sm:gap-3 mb-3">
                        <CommandButton
                            id="generate_report"
                            label="Generar Reporte"
                            icon="📄"
                            color="gray"
                            onClick={handleGenerateReport}
                            disabled={!isOnline || isExecuting}
                        />
                        <button
                            onClick={handleViewReport}
                            disabled={!lastReport}
                            className={`relative p-3 sm:p-4 rounded-xl text-center transition-all duration-200 
                                bg-gradient-to-br from-indigo-600 to-indigo-700 hover:from-indigo-500 hover:to-indigo-600 
                                border border-indigo-500/30
                                disabled:opacity-50 disabled:cursor-not-allowed 
                                active:scale-95 shadow-lg min-h-[80px] sm:min-h-[100px]`}
                        >
                            <span className="text-xl sm:text-2xl block mb-1 sm:mb-2">👁️</span>
                            <span className="text-xs sm:text-sm font-medium block leading-tight">Ver Reporte</span>
                            {lastReport && <span className="absolute top-2 right-2 w-2 h-2 bg-emerald-500 rounded-full"></span>}
                        </button>
                    </div>
                    <div className="grid grid-cols-2 gap-2 sm:gap-3">
                        <button
                            onClick={handleDownloadReport}
                            disabled={!lastReport}
                            className={`relative p-3 sm:p-4 rounded-xl text-center transition-all duration-200 
                                bg-gradient-to-br from-purple-600 to-purple-700 hover:from-purple-500 hover:to-purple-600 
                                border border-purple-500/30
                                disabled:opacity-50 disabled:cursor-not-allowed 
                                active:scale-95 shadow-lg min-h-[80px] sm:min-h-[100px]`}
                        >
                            <span className="text-xl sm:text-2xl block mb-1 sm:mb-2">📥</span>
                            <span className="text-xs sm:text-sm font-medium block leading-tight">Descargar PDF</span>
                        </button>
                        <button
                            onClick={handleWorkComplete}
                            disabled={!isOnline}
                            className="relative p-3 sm:p-4 rounded-xl text-center transition-all duration-200 
                                bg-gradient-to-br from-red-700 to-red-800 hover:from-red-600 hover:to-red-700 
                                border border-red-500/50
                                disabled:opacity-50 disabled:cursor-not-allowed 
                                active:scale-95 shadow-lg hover:shadow-red-500/20 min-h-[80px] sm:min-h-[100px]"
                        >
                            <span className="text-xl sm:text-2xl block mb-1 sm:mb-2">✅</span>
                            <span className="text-xs sm:text-sm font-bold block leading-tight">FINALIZAR</span>
                        </button>
                    </div>
                </div>
            </div>

            {/* Live Console (Matrix Style) */}
            <div className="glass rounded-xl overflow-hidden">
                <div className="bg-black/80 p-3 border-b border-gray-700 flex items-center justify-between">
                    <div className="flex items-center gap-2">
                        <span className="w-3 h-3 rounded-full bg-red-500"></span>
                        <span className="w-3 h-3 rounded-full bg-yellow-500"></span>
                        <span className="w-3 h-3 rounded-full bg-green-500"></span>
                        <span className="ml-4 text-sm text-gray-400 font-mono">Terminal de Comandos</span>
                    </div>
                    <button
                        onClick={() => setConsoleLogs([])}
                        className="text-xs text-gray-500 hover:text-gray-300"
                    >
                        Limpiar
                    </button>
                </div>
                <div
                    ref={consoleRef}
                    className="bg-black p-4 h-64 overflow-y-auto font-mono text-sm"
                    style={{ fontFamily: "'Fira Code', 'Cascadia Code', Consolas, monospace" }}
                >
                    {consoleLogs.length === 0 ? (
                        <p className="text-gray-600">
                            Esperando comandos... Presiona un botón para iniciar.
                        </p>
                    ) : (
                        consoleLogs.map((log, i) => (
                            <div key={i} className={`mb-1 ${log.type === 'error' ? 'text-red-400' :
                                log.type === 'success' ? 'text-emerald-400' :
                                    log.type === 'warning' ? 'text-amber-400' :
                                        'text-green-400'
                                }`}>
                                <span className="text-gray-500">[{log.timestamp}]</span> {log.message}
                            </div>
                        ))
                    )}
                    {isExecuting && (
                        <div className="text-green-400 animate-pulse">
                            <span className="text-gray-500">[{new Date().toLocaleTimeString('es-ES')}]</span> Procesando...
                        </div>
                    )}
                </div>
            </div>

            {/* Device Info Card */}
            <div className="glass rounded-xl p-5">
                <h3 className="font-semibold mb-4 text-gray-400">Información del Dispositivo</h3>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                    <div>
                        <p className="text-gray-500">Hostname</p>
                        <p className="font-medium">{selectedAgent.hostname || 'N/A'}</p>
                    </div>
                    <div>
                        <p className="text-gray-500">Usuario</p>
                        <p className="font-medium">{selectedAgent.username || 'N/A'}</p>
                    </div>
                    <div>
                        <p className="text-gray-500">Conectado</p>
                        <p className="font-medium">{formatDate(selectedAgent.connected_at)}</p>
                    </div>
                    <div>
                        <p className="text-gray-500">Último Heartbeat</p>
                        <p className="font-medium">{formatDate(selectedAgent.last_heartbeat)}</p>
                    </div>
                </div>
            </div>

            {/* Report Preview Modal */}
            {showReportModal && lastReport && (
                <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm">
                    <div className="bg-dark-800 rounded-2xl w-full max-w-5xl h-[90vh] flex flex-col overflow-hidden shadow-2xl border border-white/10">
                        {/* Modal Header */}
                        <div className="flex items-center justify-between p-4 border-b border-gray-700">
                            <div className="flex items-center gap-3">
                                <span className="text-2xl">📄</span>
                                <div>
                                    <h2 className="font-bold text-lg">Reporte de Servicio</h2>
                                    <p className="text-sm text-gray-400">{selectedAgent?.hostname} - {new Date().toLocaleDateString('es-ES')}</p>
                                </div>
                            </div>
                            <div className="flex items-center gap-2">
                                <button
                                    onClick={handleDownloadReport}
                                    className="px-4 py-2 bg-purple-600 hover:bg-purple-700 rounded-lg font-medium text-sm transition-colors flex items-center gap-2"
                                >
                                    📥 Descargar
                                </button>
                                <button
                                    onClick={() => setShowReportModal(false)}
                                    className="p-2 hover:bg-white/10 rounded-lg transition-colors"
                                >
                                    <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                                    </svg>
                                </button>
                            </div>
                        </div>

                        {/* Report Content */}
                        <div className="flex-1 overflow-auto bg-white">
                            <iframe
                                srcDoc={lastReport.html}
                                title="Reporte"
                                className="w-full h-full border-0"
                                style={{ minHeight: '100%' }}
                            />
                        </div>
                    </div>
                </div>
            )}
        </div>
    )
}

function formatDate(isoString) {
    if (!isoString) return 'N/A'
    return new Date(isoString).toLocaleString('es-ES')
}
