import React, { useState, useRef } from 'react';
import {
  Box,
  Button,
  Card,
  CardBody,
  CardHeader,
  Heading,
  Text,
  VStack,
  HStack,
  IconButton,
  Modal,
  ModalOverlay,
  ModalContent,
  ModalHeader,
  ModalBody,
  ModalFooter,
  ModalCloseButton,
  FormControl,
  FormLabel,
  FormErrorMessage,
  Input,
  useDisclosure,
  useToast,
  Spinner,
  Badge,
  AlertDialog,
  AlertDialogBody,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogContent,
  AlertDialogOverlay,
  Table,
  Thead,
  Tbody,
  Tr,
  Th,
  Td,
  TableContainer,
  Flex,
} from '@chakra-ui/react';
import { EditIcon, DeleteIcon } from '@chakra-ui/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { authApi } from '@/api/client';
import { useNavigate } from 'react-router-dom';
import { useUploadCV } from '@/hooks/useLetter';

// Types
interface CV {
  id: number;
  source_id: string;
  filename: string;
  original_filename: string;
  file_size: number;
  content_type: string;
  status: string;
  created_at: string;
  updated_at: string;
}

interface CVListResponse {
  success: boolean;
  data: {
    cvs: CV[];
  };
}

interface CVUpdateRequest {
  cv_id: number;
  source_id: string;
  file: File;
}

interface GeneralResponse {
  success: boolean;
  message: string;
}

// Hooks
const useUserCVs = () => {
  return useQuery<CVListResponse, Error>({
    queryKey: ['userCVs'],
    queryFn: async () => {
      const response = await authApi.get('/user/cvs');
      return response.data;
    },
  });
};

const useUpdateCV = () => {
  const queryClient = useQueryClient();
  return useMutation<GeneralResponse, Error, CVUpdateRequest>({
    mutationFn: async (data: CVUpdateRequest) => {
      const formData = new FormData();
      formData.append('source_id', data.source_id);
      formData.append('file', data.file);

      const response = await authApi.put(`/cv/${data.cv_id}`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['userCVs'] });
    },
  });
};

const useDeleteCV = () => {
  const queryClient = useQueryClient();
  return useMutation<GeneralResponse, Error, number>({
    mutationFn: async (cvId: number) => {
      const response = await authApi.delete(`/cv/${cvId}`);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['userCVs'] });
    },
  });
};

// Format file size
const formatFileSize = (bytes: number): string => {
  if (bytes === 0) return '0 Bytes';
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
};

// Format date
const formatDate = (dateString: string): string => {
  return new Date(dateString).toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
};

// Edit Modal Component
interface EditModalProps {
  isOpen: boolean;
  onClose: () => void;
  cv: CV | null;
  onUpdate: (data: CVUpdateRequest) => void;
  isUpdating: boolean;
}

const EditCVModal: React.FC<EditModalProps> = ({
  isOpen,
  onClose,
  cv,
  onUpdate,
  isUpdating,
}) => {
  const { t } = useTranslation();
  const [file, setFile] = useState<File | null>(null);
  const [errors, setErrors] = useState<{ file?: string }>({});

  React.useEffect(() => {
    if (cv) {
      setFile(null);
      setErrors({});
    }
  }, [cv]);

  const validate = (): boolean => {
    const newErrors: { file?: string } = {};

    if (!file) {
      newErrors.file = t('cvs.editModal.fileRequired');
    } else if (file.type !== 'application/pdf') {
      newErrors.file = t('cvs.editModal.onlyPdf');
    } else if (file.size > 10 * 1024 * 1024) {
      newErrors.file = t('cvs.editModal.maxSize');
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = () => {
    if (validate() && cv && file) {
      const sourceId = Date.now().toString();
      onUpdate({
        cv_id: cv.id,
        source_id: sourceId,
        file: file,
      });
    }
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} size="lg">
      <ModalOverlay />
      <ModalContent>
        <ModalHeader>{t('cvs.editModal.title')}</ModalHeader>
        <ModalCloseButton />
        <ModalBody>
          <VStack spacing={4}>
            <FormControl isInvalid={!!errors.file}>
              <FormLabel>{t('cvs.editModal.newFile')}</FormLabel>
              <Input
                type="file"
                accept=".pdf"
                onChange={(e) => setFile(e.target.files?.[0] || null)}
              />
              <FormErrorMessage>{errors.file}</FormErrorMessage>
              {cv && (
                <Text fontSize="sm" color="gray.500" mt={1}>
                  {t('cvs.editModal.currentFile')} {cv.original_filename}
                </Text>
              )}
            </FormControl>
          </VStack>
        </ModalBody>

        <ModalFooter>
          <Button variant="ghost" mr={3} onClick={onClose}>
            {t('cvs.editModal.cancel')}
          </Button>
          <Button
            colorScheme="blue"
            onClick={handleSubmit}
            isLoading={isUpdating}
            loadingText={t('cvs.editModal.updating')}
          >
            {t('cvs.editModal.update')}
          </Button>
        </ModalFooter>
      </ModalContent>
    </Modal>
  );
};

// Upload Modal Component
interface UploadModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

const UploadCVModal: React.FC<UploadModalProps> = ({
  isOpen,
  onClose,
  onSuccess,
}) => {
  const { t } = useTranslation();
  const [file, setFile] = useState<File | null>(null);
  const [errors, setErrors] = useState<{ file?: string }>({});
  const toast = useToast();
  const uploadCV = useUploadCV();

  React.useEffect(() => {
    if (isOpen) {
      setFile(null);
      setErrors({});
    }
  }, [isOpen]);

  const validate = (): boolean => {
    const newErrors: { file?: string } = {};

    if (!file) {
      newErrors.file = t('cvs.uploadModal.fileRequired');
    } else if (file.type !== 'application/pdf') {
      newErrors.file = t('cvs.uploadModal.onlyPdf');
    } else if (file.size > 10 * 1024 * 1024) {
      newErrors.file = t('cvs.uploadModal.maxSize');
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = () => {
    if (validate() && file) {
      uploadCV.mutate({ file }, {
        onSuccess: (data) => {
          if (data.success) {
            toast({
              title: t('cvs.toast.uploadedTitle'),
              description: data.message || t('cvs.toast.uploadedDesc'),
              status: 'success',
              duration: 5000,
              isClosable: true,
            });
            onSuccess();
            onClose();
          }
        },
        onError: (error) => {
          toast({
            title: t('cvs.toast.uploadFailTitle'),
            description: error.message || t('cvs.toast.uploadFailDesc'),
            status: 'error',
            duration: 5000,
            isClosable: true,
          });
        },
      });
    }
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} size="lg">
      <ModalOverlay />
      <ModalContent>
        <ModalHeader>{t('cvs.uploadModal.title')}</ModalHeader>
        <ModalCloseButton />
        <ModalBody>
          <VStack spacing={4}>
            <Text color="gray.600">
              {t('cvs.uploadModal.desc')}
            </Text>
            <FormControl isInvalid={!!errors.file}>
              <FormLabel>{t('cvs.uploadModal.fileLabel')}</FormLabel>
              <Input
                type="file"
                accept=".pdf"
                onChange={(e) => setFile(e.target.files?.[0] || null)}
              />
              <FormErrorMessage>{errors.file}</FormErrorMessage>
              <Text fontSize="sm" color="gray.500" mt={1}>
                {t('cvs.uploadModal.helperText')}
              </Text>
            </FormControl>
          </VStack>
        </ModalBody>

        <ModalFooter>
          <Button variant="ghost" mr={3} onClick={onClose}>
            {t('cvs.uploadModal.cancel')}
          </Button>
          <Button
            colorScheme="blue"
            onClick={handleSubmit}
            isLoading={uploadCV.isPending}
            loadingText={t('cvs.uploadModal.uploading')}
            isDisabled={!file}
          >
            {t('cvs.uploadModal.upload')}
          </Button>
        </ModalFooter>
      </ModalContent>
    </Modal>
  );
};

// Main Component
const UserCVPage: React.FC = () => {
  const toast = useToast();
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const { isOpen: isEditOpen, onOpen: onEditOpen, onClose: onEditClose } = useDisclosure();
  const { isOpen: isDeleteOpen, onOpen: onDeleteOpen, onClose: onDeleteClose } = useDisclosure();
  const { isOpen: isUploadOpen, onOpen: onUploadOpen, onClose: onUploadClose } = useDisclosure();
  const cancelRef = useRef<HTMLButtonElement>(null);

  const [selectedCV, setSelectedCV] = useState<CV | null>(null);
  const navigate = useNavigate();
  const { data, isLoading, isError, error } = useUserCVs();
  const updateCV = useUpdateCV();
  const deleteCV = useDeleteCV();

  const handleEditClick = (cv: CV) => {
    setSelectedCV(cv);
    onEditOpen();
  };

  const handleUploadSuccess = () => {
    queryClient.invalidateQueries({ queryKey: ['userCVs'] });
  };

  const handleDeleteClick = (cv: CV) => {
    setSelectedCV(cv);
    onDeleteOpen();
  };

  const handleUpdate = (data: CVUpdateRequest) => {
    updateCV.mutate(data, {
      onSuccess: (response) => {
        toast({
          title: t('cvs.toast.updatedTitle'),
          description: response.message || t('cvs.toast.updatedDesc'),
          status: 'success',
          duration: 5000,
          isClosable: true,
        });
        onEditClose();
      },
      onError: (error) => {
        toast({
          title: t('cvs.toast.updateFailTitle'),
          description: error.message || t('cvs.toast.updateFailDesc'),
          status: 'error',
          duration: 5000,
          isClosable: true,
        });
      },
    });
  };

  const handleDelete = () => {
    if (selectedCV) {
      deleteCV.mutate(selectedCV.id, {
        onSuccess: (response) => {
          toast({
            title: t('cvs.toast.deletedTitle'),
            description: response.message || t('cvs.toast.deletedDesc'),
            status: 'success',
            duration: 5000,
            isClosable: true,
          });
          onDeleteClose();
        },
        onError: (error) => {
          toast({
            title: t('cvs.toast.deleteFailTitle'),
            description: error.message || t('cvs.toast.deleteFailDesc'),
            status: 'error',
            duration: 5000,
            isClosable: true,
          });
        },
      });
    }
  };

  const cvs = data?.data?.cvs || [];

  if (isLoading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minH="400px">
        <Spinner size="xl" />
      </Box>
    );
  }

  if (isError) {
    return (
      <Box maxW="800px" mx="auto" mt={8} p={4}>
        <Card bg="red.50">
          <CardBody>
            <Text color="red.600">
              {t('cvs.loadError')} {error?.message || t('cvs.unknownError')}
            </Text>
          </CardBody>
        </Card>
      </Box>
    );
  }

  return (
    <Box maxW="1000px" mx="auto" mt={8} p={4}>
      <Flex>
        <Button onClick={() => navigate('/')}>{t('cvs.generateLetter')}</Button>
      </Flex>
      <Heading mb={6} textAlign="center">
        {t('cvs.title')}
      </Heading>

      <Text mb={6} textAlign="center" color="gray.600">
        {t('cvs.subtitle')}
      </Text>
      <Flex my="4">
        <Button colorScheme="blue" onClick={onUploadOpen}>
          {t('cvs.uploadNew')}
        </Button>
      </Flex>
      {cvs.length === 0 ? (
        <Card>
          <CardBody>
            <Text textAlign="center" color="gray.500">
              {t('cvs.noResumes')}
            </Text>
          </CardBody>
        </Card>
      ) : (
        <Card>
          <CardHeader>
            <Heading size="md">{t('cvs.uploadedCount', { count: cvs.length })}</Heading>
          </CardHeader>
          <CardBody>
            <TableContainer>
              <Table variant="simple">
                <Thead>
                  <Tr>
                    <Th>{t('cvs.filename')}</Th>
                    <Th>{t('cvs.sourceId')}</Th>
                    <Th>{t('cvs.size')}</Th>
                    <Th>{t('cvs.status')}</Th>
                    <Th>{t('cvs.uploaded')}</Th>
                    <Th>{t('cvs.actions')}</Th>
                  </Tr>
                </Thead>
                <Tbody>
                  {cvs.map((cv) => (
                    <Tr key={cv.id}>
                      <Td>
                        <Text fontWeight="medium" noOfLines={1} maxW="200px">
                          {cv.original_filename}
                        </Text>
                      </Td>
                      <Td>
                        <Text fontSize="sm" color="gray.600">
                          {cv.source_id}
                        </Text>
                      </Td>
                      <Td>
                        <Text fontSize="sm">{formatFileSize(cv.file_size)}</Text>
                      </Td>
                      <Td>
                        <Badge
                          colorScheme={
                            cv.status === 'processed'
                              ? 'green'
                              : cv.status === 'error'
                              ? 'red'
                              : 'yellow'
                          }
                        >
                          {cv.status}
                        </Badge>
                      </Td>
                      <Td>
                        <Text fontSize="sm">{formatDate(cv.created_at)}</Text>
                      </Td>
                      <Td>
                        <HStack spacing={2}>
                          <IconButton
                            aria-label={t('cvs.editAriaLabel')}
                            icon={<EditIcon />}
                            size="sm"
                            colorScheme="blue"
                            variant="ghost"
                            onClick={() => handleEditClick(cv)}
                          />
                          <IconButton
                            aria-label={t('cvs.deleteAriaLabel')}
                            icon={<DeleteIcon />}
                            size="sm"
                            colorScheme="red"
                            variant="ghost"
                            onClick={() => handleDeleteClick(cv)}
                          />
                        </HStack>
                      </Td>
                    </Tr>
                  ))}
                </Tbody>
              </Table>
            </TableContainer>
          </CardBody>
        </Card>
      )}

      {/* Edit Modal */}
      <EditCVModal
        isOpen={isEditOpen}
        onClose={onEditClose}
        cv={selectedCV}
        onUpdate={handleUpdate}
        isUpdating={updateCV.isPending}
      />

      {/* Delete Confirmation Dialog */}
      <AlertDialog
        isOpen={isDeleteOpen}
        leastDestructiveRef={cancelRef}
        onClose={onDeleteClose}
      >
        <AlertDialogOverlay>
          <AlertDialogContent>
            <AlertDialogHeader fontSize="lg" fontWeight="bold">
              {t('cvs.deleteModal.title')}
            </AlertDialogHeader>

            <AlertDialogBody>
              {t('cvs.deleteModal.body', { name: selectedCV?.original_filename ?? '' })}
            </AlertDialogBody>

            <AlertDialogFooter>
              <Button ref={cancelRef} onClick={onDeleteClose}>
                {t('cvs.deleteModal.cancel')}
              </Button>
              <Button
                colorScheme="red"
                onClick={handleDelete}
                ml={3}
                isLoading={deleteCV.isPending}
                loadingText={t('cvs.deleteModal.deleting')}
              >
                {t('cvs.deleteModal.delete')}
              </Button>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialogOverlay>
      </AlertDialog>

      {/* Upload Modal */}
      <UploadCVModal
        isOpen={isUploadOpen}
        onClose={onUploadClose}
        onSuccess={handleUploadSuccess}
      />
    </Box>
  );
};

export default UserCVPage;
