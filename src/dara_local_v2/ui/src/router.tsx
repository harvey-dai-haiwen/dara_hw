import { Navigate, createBrowserRouter } from 'react-router-dom'

import { AppLayout } from './components/AppLayout'
import { JobDetailPage } from './pages/JobDetailPage'
import { ResultsPage } from './pages/ResultsPage'
import { SearchPage } from './pages/SearchPage'
import { TutorialPage } from './pages/TutorialPage'

export const router = createBrowserRouter([
  {
    path: '/',
    element: <AppLayout />,
    children: [
      { index: true, element: <Navigate to="/search" replace /> },
      { path: 'search', element: <SearchPage /> },
      { path: 'results', element: <ResultsPage /> },
      { path: 'results/:jobId', element: <JobDetailPage /> },
      { path: 'tutorial', element: <TutorialPage /> },
      { path: '*', element: <Navigate to="/search" replace /> },
    ],
  },
])
