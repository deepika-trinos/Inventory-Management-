// Short pop-up messages ("snackbars") at the bottom of the screen, e.g.
// "Vendor saved". Any screen can call:
//
//   const notify = useNotify()
//   notify.success('Vendor saved')
//   notify.error('Could not save the vendor')
import { createContext, useCallback, useContext, useMemo, useState } from 'react'
import { Alert, Snackbar } from '@mui/material'

const NotificationContext = createContext(null)

export function NotificationProvider({ children }) {
  const [message, setMessage] = useState(null) // { text, severity, key }

  const show = useCallback((text, severity) => {
    setMessage({ text, severity, key: Date.now() })
  }, [])

  const notify = useMemo(
    () => ({
      success: (text) => show(text, 'success'),
      error: (text) => show(text, 'error'),
      info: (text) => show(text, 'info'),
    }),
    [show],
  )

  const handleClose = (_event, reason) => {
    if (reason !== 'clickaway') setMessage(null)
  }

  return (
    <NotificationContext.Provider value={notify}>
      {children}
      <Snackbar
        key={message?.key}
        open={Boolean(message)}
        autoHideDuration={message?.severity === 'error' ? 8000 : 4000}
        onClose={handleClose}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
      >
        {message ? (
          <Alert onClose={handleClose} severity={message.severity} variant="filled" sx={{ width: '100%' }}>
            {message.text}
          </Alert>
        ) : undefined}
      </Snackbar>
    </NotificationContext.Provider>
  )
}

export function useNotify() {
  const context = useContext(NotificationContext)
  if (!context) throw new Error('useNotify must be used inside <NotificationProvider>')
  return context
}
