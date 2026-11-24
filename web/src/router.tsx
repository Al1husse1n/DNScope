import { createBrowserRouter } from 'react-router-dom';
import { HomePage } from './pages/HomePage';
import { SharedResultPage } from './pages/SharedResultPage';
import { KeyEntryPage } from './pages/KeyEntryPage';
import { InvestigationsListPage } from './pages/InvestigationsListPage';
import { InvestigationDetailPage } from './pages/InvestigationDetailPage';
import { NotFoundPage } from './pages/NotFoundPage';
import { ProtectedRoute } from './components/ProtectedRoute';

export const router = createBrowserRouter([
  {
    path: '/',
    element: <HomePage />,
  },
  {
    path: '/r/:shareId',
    element: <SharedResultPage />,
  },
  {
    path: '/key',
    element: <KeyEntryPage />,
  },
  {
    path: '/dashboard',
    element: <ProtectedRoute />,
    children: [
      {
        index: true,
        element: <InvestigationsListPage />,
      },
      {
        path: 'investigations/:id',
        element: <InvestigationDetailPage />,
      },
      {
        path: '*',
        element: <NotFoundPage />,
      },
    ],
  },
  {
    path: '/investigations/:id',
    element: <ProtectedRoute />,
    children: [
      {
        index: true,
        element: <InvestigationDetailPage />,
      },
    ],
  },
  {
    path: '*',
    element: <NotFoundPage />,
  },
]);
