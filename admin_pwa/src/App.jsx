import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { useAuthStore } from './stores/authStore'
import Login from './views/Login'
import Dashboard from './views/Dashboard'
import AgentDetail from './views/AgentDetail'
import Layout from './components/Layout'

function ProtectedRoute({ children }) {
    const { isAuthenticated } = useAuthStore()

    if (!isAuthenticated) {
        return <Navigate to="/login" replace />
    }

    return children
}

function App() {
    return (
        <BrowserRouter>
            <Routes>
                <Route path="/login" element={<Login />} />
                <Route path="/" element={
                    <ProtectedRoute>
                        <Layout />
                    </ProtectedRoute>
                }>
                    <Route index element={<Dashboard />} />
                    <Route path="agent/:agentId" element={<AgentDetail />} />
                </Route>
            </Routes>
        </BrowserRouter>
    )
}

export default App
