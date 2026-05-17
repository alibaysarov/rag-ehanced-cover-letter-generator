import { Routes, Route, Navigate } from 'react-router-dom';

import LoginPage from '@/features/auth/components/LoginPage';
import RegisterPage from '@/features/auth/components/RegisterPage';
import PrivateRoute from '@/features/auth/components/PrivateRoute';

import CVUploadPage from '@/pages/CVUploadPage';
import LetterGenerator from '@/pages/LetterGenerator';
import UserCVPage from '@/pages/UserCVPage';
import ProjectsPage from '@/pages/ProjectsPage';
import ProfilePage from '@/pages/ProfilePage';
import StatsPage from '@/pages/StatsPage';
import AutoParsePage from '@/pages/AutoParsePage';

import AppShell from '@/layouts/AppShell';

function App() {
  const handleUploadSuccess = (_uploadedSourceId: number) => {
    // CVUploadPage may handle its own post-upload navigation in a later wave.
  };

  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />

      <Route
        path="/"
        element={
          <PrivateRoute>
            <AppShell>
              <LetterGenerator />
            </AppShell>
          </PrivateRoute>
        }
      />
      <Route
        path="/projects"
        element={
          <PrivateRoute>
            <AppShell>
              <ProjectsPage />
            </AppShell>
          </PrivateRoute>
        }
      />
      <Route
        path="/my-cvs"
        element={
          <PrivateRoute>
            <AppShell>
              <UserCVPage />
            </AppShell>
          </PrivateRoute>
        }
      />
      <Route
        path="/upload-cv"
        element={
          <PrivateRoute>
            <AppShell>
              <CVUploadPage onUploadSuccess={handleUploadSuccess} />
            </AppShell>
          </PrivateRoute>
        }
      />
      <Route
        path="/profile"
        element={
          <PrivateRoute>
            <AppShell>
              <ProfilePage />
            </AppShell>
          </PrivateRoute>
        }
      />
      <Route
        path="/stats"
        element={
          <PrivateRoute>
            <AppShell>
              <StatsPage />
            </AppShell>
          </PrivateRoute>
        }
      />

      <Route
        path="/auto-parse"
        element={
          <PrivateRoute>
            <AppShell>
              <AutoParsePage />
            </AppShell>
          </PrivateRoute>
        }
      />

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

export default App;
