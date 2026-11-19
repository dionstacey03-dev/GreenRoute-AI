import { useState } from 'react'
import { Show, SignIn, SignUp, UserButton } from '@clerk/react'
import './AuthShell.css'

export default function AuthShell({ children }) {
  const [mode, setMode] = useState('sign-in')

  return (
    <>
      <Show when="signed-out">
        <main className="gr-auth-layout">
          <section className="gr-auth-intro">
            <p className="gr-auth-eyebrow">GREENROUTE AI · V3</p>
            <h1>Move smarter.<br />Travel greener.</h1>
            <p className="gr-auth-description">
              Sign in to save your journeys securely and keep your sustainable
              travel estimates connected to your account.
            </p>
            <div className="gr-auth-points">
              <span>01 / Plan smarter routes</span>
              <span>02 / Keep your journey history</span>
              <span>03 / Track estimated impact</span>
            </div>
          </section>

          <section className="gr-auth-card" aria-label="Account authentication">
            <div className="gr-auth-tabs" role="group" aria-label="Authentication mode">
              <button
                type="button"
                className={mode === 'sign-in' ? 'active' : ''}
                onClick={() => setMode('sign-in')}
              >
                Sign in
              </button>
              <button
                type="button"
                className={mode === 'sign-up' ? 'active' : ''}
                onClick={() => setMode('sign-up')}
              >
                Create account
              </button>
            </div>
            {mode === 'sign-in' ? <SignIn /> : <SignUp />}
          </section>
        </main>
      </Show>

      <Show when="signed-in">
        <div className="gr-authenticated">
          <div className="gr-user-control" aria-label="Account menu">
            <UserButton />
          </div>
          {children}
        </div>
      </Show>
    </>
  )
}
