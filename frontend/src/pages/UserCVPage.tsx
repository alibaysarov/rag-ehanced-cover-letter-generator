

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
      newErrors.file = 'PDF file is required';
    } else if (file.type !== 'application/pdf') {
      newErrors.file = 'Only PDF files are allowed';
    } else if (file.size > 10 * 1024 * 1024) {
      newErrors.file = 'File size must be less than 10MB';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = () => {
    if (validate() && cv && file) {
      // Generate source_id automatically like in CVUploadPage
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
        <ModalHeader>Edit CV</ModalHeader>
        <ModalCloseButton />
        <ModalBody>
          <VStack spacing={4}>
            <FormControl isInvalid={!!errors.file}>
              <FormLabel>New PDF File</FormLabel>
              <Input
                type="file"
                accept=".pdf"
                onChange={(e) => setFile(e.target.files?.[0] || null)}
              />
              <FormErrorMessage>{errors.file}</FormErrorMessage>
              {cv && (
                <Text fontSize="sm" color="gray.500" mt={1}>
                  Current file: {cv.original_filename}
                </Text>
              )}
            </FormControl>
          </VStack>
        </ModalBody>

        <ModalFooter>
          <Button variant="ghost" mr={3} onClick={onClose}>
            Cancel
          </Button>
          <Button
            colorScheme="blue"
            onClick={handleSubmit}
            isLoading={isUpdating}
            loadingText="Updating..."
          >
            Update CV
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
      newErrors.file = 'PDF file is required';
    } else if (file.type !== 'application/pdf') {
      newErrors.file = 'Only PDF files are allowed';
    } else if (file.size > 10 * 1024 * 1024) {
      newErrors.file = 'File size must be less than 10MB';
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
              title: 'CV Uploaded',
              description: data.message || 'CV has been uploaded successfully.',
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
            title: 'Upload Failed',
            description: error.message || 'Failed to upload CV. Please try again.',
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
        <ModalHeader>Upload New Resume</ModalHeader>
        <ModalCloseButton />
        <ModalBody>
          <VStack spacing={4}>
            <Text color="gray.600">
              Upload your resume in PDF format to get started with cover letter generation.
            </Text>
            <FormControl isInvalid={!!errors.file}>
              <FormLabel>Resume File (PDF)</FormLabel>
              <Input
                type="file"
                accept=".pdf"
                onChange={(e) => setFile(e.target.files?.[0] || null)}
              />
              <FormErrorMessage>{errors.file}</FormErrorMessage>
              <Text fontSize="sm" color="gray.500" mt={1}>
                Only PDF files are supported. Maximum size: 10MB.
              </Text>
            </FormControl>
          </VStack>
        </ModalBody>

        <ModalFooter>
          <Button variant="ghost" mr={3} onClick={onClose}>
            Cancel
          </Button>
          <Button
            colorScheme="blue"
            onClick={handleSubmit}
            isLoading={uploadCV.isPending}
            loadingText="Uploading..."
            isDisabled={!file}
          >
            Upload Resume
          </Button>
        </ModalFooter>
      </ModalContent>
    </Modal>
  );
};

// Main Component
const UserCVPage: React.FC = () => {
  const toast = useToast();
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
          title: 'CV Updated',
          description: response.message || 'CV has been updated successfully.',
          status: 'success',
          duration: 5000,
          isClosable: true,
        });
        onEditClose();
      },
      onError: (error) => {
        toast({
          title: 'Update Failed',
          description: error.message || 'Failed to update CV. Please try again.',
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
            title: 'CV Deleted',
            description: response.message || 'CV has been deleted successfully.',
            status: 'success',
            duration: 5000,
            isClosable: true,
          });
          onDeleteClose();
        },
        onError: (error) => {
          toast({
            title: 'Delete Failed',
            description: error.message || 'Failed to delete CV. Please try again.',
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
              Error loading CVs: {error?.message || 'Unknown error'}
            </Text>
          </CardBody>
        </Card>
      </Box>
    );
  }

  return (
    <Box maxW="1000px" mx="auto" mt={8} p={4}>
        <Flex>
            <Button onClick={() => navigate('/')}>Generate letter</Button>
        </Flex>
      <Heading mb={6} textAlign="center">
        My Resumes
      </Heading>

      <Text mb={6} textAlign="center" color="gray.600">
        Manage your uploaded resumes here.
      </Text>
        <Flex my="4">
        <Button colorScheme="blue" onClick={onUploadOpen}>
          Upload New Resume
        </Button>
        </Flex>
      {cvs.length === 0 ? (
        <Card>
          <CardBody>
            <Text textAlign="center" color="gray.500">
              No resumes uploaded yet. Upload your first resume to get started.
            </Text>
          </CardBody>
        </Card>
      ) : (
        <Card>
          <CardHeader>
            <Heading size="md">Uploaded Resumes ({cvs.length})</Heading>
          </CardHeader>
          <CardBody>
            <TableContainer>
              <Table variant="simple">
                <Thead>
                  <Tr>
                    <Th>Filename</Th>
                    <Th>Source ID</Th>
                    <Th>Size</Th>
                    <Th>Status</Th>
                    <Th>Uploaded</Th>
                    <Th>Actions</Th>
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
                            aria-label="Edit CV"
                            icon={<EditIcon />}
                            size="sm"
                            colorScheme="blue"
                            variant="ghost"
                            onClick={() => handleEditClick(cv)}
                          />
                          <IconButton
                            aria-label="Delete CV"
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
              Delete CV
            </AlertDialogHeader>

            <AlertDialogBody>
              Are you sure you want to delete "{selectedCV?.original_filename}"? This
              action cannot be undone.
            </AlertDialogBody>

            <AlertDialogFooter>
              <Button ref={cancelRef} onClick={onDeleteClose}>
                Cancel
              </Button>
              <Button
                colorScheme="red"
                onClick={handleDelete}
                ml={3}
                isLoading={deleteCV.isPending}
                loadingText="Deleting..."
              >
                Delete
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