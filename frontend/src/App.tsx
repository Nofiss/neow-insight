import { Navigate, NavLink, Outlet, Route, Routes, useMatch, useParams } from 'react-router-dom'
import { OverviewPage } from '@/pages/overview-page'
import { RecommendationPage } from '@/pages/recommendation-page'
import { RunDetailPage } from '@/pages/run-detail-page'
import { RunsPage } from '@/pages/runs-page'

function AppShell() {
  const runDetailMatch = useMatch('/runs/:runId')
  const { runId } = useParams<{ runId: string }>()
  const decodedRunId = runId ? decodeURIComponent(runId) : null

  return (
    <div className="min-h-dvh">
      <header className="sticky top-0 z-10 border-b border-zinc-300/90 bg-white/90 backdrop-blur">
        <div className="mx-auto flex w-full max-w-6xl flex-col gap-4 px-4 py-4 sm:px-6 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <p className="text-xs font-semibold tracking-[0.2em] text-zinc-500 uppercase">
              Neow's Insight
            </p>
            <div className="flex flex-wrap items-center gap-2">
              <h1 className="text-2xl font-semibold text-zinc-900">Decision Hub</h1>
              {runDetailMatch && decodedRunId ? (
                <span className="rounded-full border border-amber-300 bg-amber-100 px-2 py-0.5 text-xs font-semibold text-amber-900">
                  Run detail: {decodedRunId}
                </span>
              ) : null}
            </div>
          </div>
          <nav className="flex flex-wrap items-center gap-2 text-sm">
            {[
              { to: '/overview', label: 'Overview' },
              { to: '/recommendation', label: 'Recommendation' },
              { to: '/runs', label: 'Runs' },
            ].map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) =>
                  `rounded-md border px-3 py-1.5 transition ${
                    isActive
                      ? 'border-amber-300 bg-amber-100 text-amber-900'
                      : 'border-zinc-300 bg-white text-zinc-700 hover:bg-zinc-100'
                  }`
                }
              >
                {item.label}
              </NavLink>
            ))}
          </nav>
        </div>
      </header>
      <Outlet />
    </div>
  )
}

function App() {
  return (
    <Routes>
      <Route element={<AppShell />}>
        <Route index element={<Navigate to="/overview" replace />} />
        <Route path="/overview" element={<OverviewPage />} />
        <Route path="/recommendation" element={<RecommendationPage />} />
        <Route path="/runs" element={<RunsPage />} />
        <Route path="/runs/:runId" element={<RunDetailPage />} />
      </Route>
      <Route path="*" element={<Navigate to="/overview" replace />} />
    </Routes>
  )
}

export default App
