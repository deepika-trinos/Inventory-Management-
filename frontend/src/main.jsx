// Entry point: puts the React app into the <div id="root"> in index.html.
// The "providers" wrap the whole app so every screen can use them:
//   ThemeProvider        : shared colours and fonts (MUI)
//   BrowserRouter        : page addresses (React Router)
//   NotificationProvider : pop-up success/error messages
//   AuthProvider         : who is logged in
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router'
import { CssBaseline, ThemeProvider } from '@mui/material'

import { AuthProvider } from './context/AuthContext'
import { NotificationProvider } from './context/NotificationContext'
import AppRoutes from './routes/AppRoutes'
import theme from './theme'

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <BrowserRouter>
        <NotificationProvider>
          <AuthProvider>
            <AppRoutes />
          </AuthProvider>
        </NotificationProvider>
      </BrowserRouter>
    </ThemeProvider>
  </StrictMode>,
)
