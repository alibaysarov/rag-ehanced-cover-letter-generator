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
import { useTranslation } from 'react-i18next';
import { useUploadCV } from '@/hooks/useLetter';

interface CVUploadPageProps {
  onUploadSuccess: (sourceId: number) => void;
}

const CVUploadPage: React.FC<CVUploadPageProps> = ({ onUploadSuccess }) => {
  const { t } = useTranslation();
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
        {t('cvs.uploadModal.title')}
      </Heading>

      <Text mb={6} textAlign="center" color="gray.600">
        {t('cvs.uploadModal.desc')}
      </Text>

      <Card>
        <CardHeader>
          <Heading size="md">{t('cvs.uploadModal.title')}</Heading>
        </CardHeader>
        <CardBody>
          <form onSubmit={handleSubmit}>
            <VStack spacing={4}>
              <FormControl isRequired>
                <FormLabel>{t('cvs.uploadModal.fileLabel')}</FormLabel>
                <Input
                  type="file"
                  accept=".pdf"
                  onChange={(e) => setFile(e.target.files?.[0] || null)}
                />
                <FormHelperText>
                  {t('cvs.uploadModal.helperText')}
                </FormHelperText>
              </FormControl>

              <Button
                type="submit"
                colorScheme="blue"
                isLoading={uploadCV.isPending}
                loadingText={t('cvs.uploadModal.uploading')}
                width="full"
                disabled={!file}
              >
                {t('cvs.uploadModal.upload')}
              </Button>
            </VStack>
          </form>
        </CardBody>
      </Card>

      {uploadCV.isError && (
        <Alert status="error" mt={4}>
          <AlertIcon />
          <AlertTitle>{t('cvs.toast.uploadFailTitle')}</AlertTitle>
          <AlertDescription>
            {uploadCV.error.message}
          </AlertDescription>
        </Alert>
      )}

      {uploadCV.isSuccess && uploadCV.data?.success && (
        <Alert status="success" mt={4}>
          <AlertIcon />
          <AlertTitle>{t('cvs.toast.uploadedTitle')}</AlertTitle>
          <AlertDescription>
            {t('cvs.toast.uploadedDesc')} Resume ID: {uploadCV.data.source_id}
          </AlertDescription>
        </Alert>
      )}
    </Box>
  );
};

export default CVUploadPage;
