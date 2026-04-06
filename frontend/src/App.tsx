import { useState } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { Box } from '@chakra-ui/react';

// Auth components
import LoginPage from '@/features/auth/components/LoginPage';
import RegisterPage from '@/features/auth/components/RegisterPage';
import PrivateRoute from '@/features/auth/components/PrivateRoute';
import Navigation from '@/features/auth/components/Navigation';

// Main app components
import CVUploadPage from '@/pages/CVUploadPage';
import LetterGenerator from '@/pages/LetterGenerator';
import UserCVPage from './pages/UserCVPage';

function App() {
  const [_, setSourceId] = useState<number | null>(null);

  const handleUploadSuccess = (uploadedSourceId: number) => {
    setSourceId(uploadedSourceId);
  };

  const handleBackToUpload = () => {
    setSourceId(null);
  };

  return (
    <Box minH="100vh" bg="gray.50">
      <Routes>
        {/* Public routes */}
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />

        {/* Protected routes */}
        <Route path="/" element={
          <PrivateRoute>
            <LetterGenerator onBack={handleBackToUpload} />
          </PrivateRoute>
        } />
        <Route
          path="/my-cvs"
          element={<UserCVPage />}

        />
        <Route
          path="/upload-cv"
          element={
            <PrivateRoute>
              <Box>
                <Navigation />
                <Box pt={4}>
                  <CVUploadPage onUploadSuccess={handleUploadSuccess} />
                </Box>
              </Box>
            </PrivateRoute>
          }
        />

        {/* Redirect root to main app */}
        <Route path="/" element={<Navigate to="/" replace />} />

        {/* Catch all route */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Box>
  );
}

export default App;
