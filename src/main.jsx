import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { ClerkProvider } from '@clerk/react'
import './index.css'
import App from './App.jsx'
import AuthShell from './auth/AuthShell.jsx'

const publishableKey = import.meta.env.VITE_CLERK_PUBLISHABLE_KEY

function Root() {
  if (!publishableKey) {
    return (
      <main className="gr-auth-config">
        <section>
          <p className="gr-auth-eyebrow">GREENROUTE AI · V3</p>
          <h1>Authentication setup required</h1>
          <p>
            Add your Clerk publishable key to the project-root <code>.env</code>
            file as <code>VITE_CLERK_PUBLISHABLE_KEY</code>, then restart Vite.
          </p>
          <p className="gr-auth-config-note">
            The application is locked until Clerk is configured. No unauthenticated
            access to account features is allowed.
          </p>
        </section>
      </main>
    )
  }

  return (
    <ClerkProvider publishableKey={publishableKey}>
      <AuthShell>
        <App />
      </AuthShell>
    </ClerkProvider>
  )
}

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <Root />
  </StrictMode>,
)
