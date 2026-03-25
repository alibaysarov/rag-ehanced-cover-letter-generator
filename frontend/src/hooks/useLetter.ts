import { useMutation, useQuery } from '@tanstack/react-query';
import { authApi } from '@/api/client';
import type { 
  LetterFromUrlRequest, 
  LetterFromTextRequest, 
  LetterResponse, 
  CVUploadRequest, 
  CVUploadResponse,
  CVOptionsResponse
} from '@/types/letter';

/**
 * Hook for fetching CV options
 */
export const useCVOptions = () => {
  return useQuery<CVOptionsResponse, Error>({
    queryKey: ['cvOptions'],
    queryFn: async () => {
      const response = await authApi.get('/user/cvs/options');
      return response.data;
    },
  });
};

/**
 * Hook for creating a letter from URL
 */
export const useCreateLetterFromUrl = () => {
  return useMutation<LetterResponse, Error, LetterFromUrlRequest>({
    mutationFn: async (data: LetterFromUrlRequest) => {
      const formData = new FormData();
      formData.append('url', data.url);
      formData.append('source_id', data.source_id.toString());

      if (data.file) {
        formData.append('file', data.file);
      }

      const response = await authApi.post('/letter/url', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });

      return response.data;
    },
    onError: (error) => {
      console.error('Error creating letter from URL:', error);
    },
  });
};

/**
 * Hook for creating a letter from text
 */
export const useCreateLetterFromText = () => {
  return useMutation<LetterResponse, Error, LetterFromTextRequest>({
    mutationFn: async (data: LetterFromTextRequest) => {
      const formData = new FormData();
      formData.append('name', data.name);
      formData.append('description', data.description);
      formData.append('source_id', data.source_id.toString());

      if (data.file) {
        formData.append('file', data.file);
      }

      const response = await authApi.post('/letter/text', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });

      return response.data;
    },
    onError: (error) => {
      console.error('Error creating letter from text:', error);
    },
  });
};

/**
 * Hook for uploading CV/resume
 */
export const useUploadCV = () => {
  return useMutation<CVUploadResponse, Error, CVUploadRequest>({
    mutationFn: async (data: CVUploadRequest) => {
      const formData = new FormData();
      formData.append('file', data.file);

      // Generate a unique source_id (you might want to use UUID or similar)
      const sourceId = Date.now(); // Simple approach, you might want to use a proper UUID
      formData.append('source_id', sourceId.toString());

      const response = await authApi.post('/letter/upload-cv', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });

      const result = response.data;
      // Add the source_id to the response for frontend use
      result.source_id = sourceId;
      return result;
    },
    onError: (error) => {
      console.error('Error uploading CV:', error);
    },
  });
};
