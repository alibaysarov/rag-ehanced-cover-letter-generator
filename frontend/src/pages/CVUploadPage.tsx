import React, { useState } from 'react';
import {
  Box,
  Button,
  FormControl,
  FormLabel,
  FormHelperText,
  Input,
  VStack,
  Card,
  CardHeader,
  CardBody,
  Heading,
  Alert,
  AlertIcon,
  AlertTitle,
  AlertDescription,
  Text,
} from '@chakra-ui/react';
import { useUploadCV } from '@/hooks/useLetter';

interface CVUploadPageProps {
  onUploadSuccess: (sourceId: number) => void;
}

const CVUploadPage: React.FC<CVUploadPageProps> = ({ onUploadSuccess }) => {
  const [file, setFile] = useState<File | null>(null);
  const uploadCV = useUploadCV();

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (file) {
      uploadCV.mutate({ file }, {
        onSuccess: (data) => {
          if (data.success && data.source_id) {
            onUploadSuccess(data.source_id);
          }
        }
      });
    }
  };

  return (
    <Box maxW="600px" mx="auto" mt={8} p={4}>
      <Heading mb={6} textAlign="center">
        Upload Your Resume
      </Heading>

      <Text mb={6} textAlign="center" color="gray.600">
        First, upload your resume (PDF format) to get started with cover letter generation.
      </Text>

      <Card>
        <CardHeader>
          <Heading size="md">Resume Upload</Heading>
        </CardHeader>
        <CardBody>
          <form onSubmit={handleSubmit}>
            <VStack spacing={4}>
              <FormControl isRequired>
                <FormLabel>Resume File (PDF)</FormLabel>
                <Input
                  type="file"
                  accept=".pdf"
                  onChange={(e) => setFile(e.target.files?.[0] || null)}
                />
                <FormHelperText>
                  Only PDF files are supported. Maximum size: 10MB.
                </FormHelperText>
              </FormControl>

              <Button
                type="submit"
                colorScheme="blue"
                isLoading={uploadCV.isPending}
                loadingText="Uploading..."
                width="full"
                disabled={!file}
              >
                Upload Resume
              </Button>
            </VStack>
          </form>
        </CardBody>
      </Card>

      {uploadCV.isError && (
        <Alert status="error" mt={4}>
          <AlertIcon />
          <AlertTitle>Upload Failed!</AlertTitle>
          <AlertDescription>
            {uploadCV.error.message}
          </AlertDescription>
        </Alert>
      )}

      {uploadCV.isSuccess && uploadCV.data?.success && (
        <Alert status="success" mt={4}>
          <AlertIcon />
          <AlertTitle>Upload Successful!</AlertTitle>
          <AlertDescription>
            Your resume has been uploaded successfully. Resume ID: {uploadCV.data.source_id}
          </AlertDescription>
        </Alert>
      )}
    </Box>
  );
};

export default CVUploadPage;
