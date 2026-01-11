import { useEffect } from 'react'
import { Link, Outlet, useNavigate } from 'react-router-dom'
import { useAuthStore } from '../stores/authStore'
import { useAgentStore } from '../stores/agentStore'

export default function Layout() {
    const navigate = useNavigate()
    const { user, logout } = useAuthStore()
    const { connectSocket, disconnectSocket } = useAgentStore()

    useEffect(() => {
        connectSocket()
        return () => disconnectSocket()
    }, [connectSocket, disconnectSocket])

    const handleLogout = () => {
        logout()
        navigate('/login')
    }

    return (
        <div className="min-h-screen bg-dark-900">
            {/* Header */}
            <header className="sticky top-0 z-50 glass border-b border-white/5">
                <div className="max-w-7xl mx-auto px-3 sm:px-6 lg:px-8">
                    <div className="flex items-center justify-between h-14 sm:h-16">
                        {/* Logo */}
                        <Link to="/" className="flex items-center gap-2 sm:gap-3">
                            <div className="w-8 h-8 sm:w-10 sm:h-10 bg-gradient-to-br from-primary-500 to-emerald-500 rounded-lg sm:rounded-xl flex items-center justify-center shadow-lg shadow-primary-500/20">
                                <svg className="w-4 h-4 sm:w-5 sm:h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                                </svg>
                            </div>
                            <span className="font-bold text-lg sm:text-xl">Autonova</span>
                        </Link>

                        {/* User menu */}
                        <div className="flex items-center gap-2 sm:gap-4">
                            <div className="flex items-center gap-1 sm:gap-2 text-xs sm:text-sm text-gray-400">
                                <span className="w-2 h-2 bg-emerald-500 rounded-full animate-pulse"></span>
                                <span className="hidden xs:inline">Conectado</span>
                            </div>

                            <div className="flex items-center gap-2 sm:gap-3">
                                <div className="text-right hidden sm:block">
                                    <p className="text-sm font-medium">{user?.username}</p>
                                    <p className="text-xs text-gray-500 capitalize">{user?.role}</p>
                                </div>
                                <button
                                    onClick={handleLogout}
                                    className="p-2 hover:bg-white/10 rounded-lg transition-colors"
                                    title="Cerrar sesión"
                                >
                                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
                                    </svg>
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            </header>

            {/* Main content */}
            <main className="max-w-7xl mx-auto px-3 sm:px-6 lg:px-8 py-4 sm:py-8">
                <Outlet />
            </main>
        </div>
    )
}
