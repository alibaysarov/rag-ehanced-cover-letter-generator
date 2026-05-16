import { Routes, Route, Navigate } from 'react-router-dom';

import LoginPage from '@/features/auth/components/LoginPage';
import RegisterPage from '@/features/auth/components/RegisterPage';
import PrivateRoute from '@/features/auth/components/PrivateRoute';

import CVUploadPage from '@/pages/CVUploadPage';
import LetterGenerator from '@/pages/LetterGenerator';
import UserCVPage from '@/pages/UserCVPage';
import ProjectsPage from '@/pages/ProjectsPage';

import AppShell from '@/layouts/AppShell';

function ProfilePagePlaceholder() {
  return <div>Profile (pending merge)</div>;
}

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
              <ProfilePagePlaceholder />
            </AppShell>
          </PrivateRoute>
        }
      />

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

export default App;
