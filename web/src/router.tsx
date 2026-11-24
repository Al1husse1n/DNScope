import { createBrowserRouter } from 'react-router-dom';
import { KeyEntryPage } from './pages/KeyEntryPage';
import { InvestigationsListPage } from './pages/InvestigationsListPage';
import { InvestigationDetailPage } from './pages/InvestigationDetailPage';
import { NotFoundPage } from './pages/NotFoundPage';
import { ProtectedRoute } from './components/ProtectedRoute';

export const router = createBrowserRouter([
  {
    path: '/key',
    element: <KeyEntryPage />,
  },
  {
    path: '/',
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
]);
