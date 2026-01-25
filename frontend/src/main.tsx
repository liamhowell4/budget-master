import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { ThemeProvider } from '@/contexts/ThemeContext'
import { AuthProvider } from '@/contexts/AuthContext'
import { ServerProvider } from '@/contexts/ServerContext'
import App from './App'
import './index.css'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <ThemeProvider>
      <AuthProvider>
        <ServerProvider>
          <App />
        </ServerProvider>
      </AuthProvider>
    </ThemeProvider>
  </StrictMode>
)
