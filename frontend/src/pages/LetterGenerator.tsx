import React, { memo, useState } from 'react';
import {
  Box,
  Button,
  FormControl,
  FormLabel,
  FormHelperText,
  Input,
  Textarea,
  VStack,
  Card,
  CardHeader,
  CardBody,
  Heading,
  Tabs,
  TabList,
  Tab,
  TabPanels,
  TabPanel,
  Alert,
  AlertIcon,
  AlertTitle,
  AlertDescription,
  Text,
  Select,
  Spinner,
  IconButton,
  HStack,
} from '@chakra-ui/react';
import { useCreateLetterFromUrl, useCreateLetterFromText, useCVOptions } from '@/hooks/useLetter';
import type {  CVOptionsResponse } from '@/types/letter';
import { useNavigate } from 'react-router-dom';

interface LetterGeneratorProps {
  // sourceId: number;
  onBack?: () => void;
}

const OptionsList: React.FC<{ response:CVOptionsResponse|undefined }> =memo(({ response }) =>  {
  if (!response) {
    return null;
  }
 console.log("CV Options Response:", response.data);
  return (
    <>
    {response.data.options.map((cv) => (
      <option key={`${cv.value}_option`} value={cv.value}>
        {cv.name}
      </option>
    ))}
    </>
  )
}) 


const LetterGenerator: React.FC<LetterGeneratorProps> = ({ onBack }) => {
  const [url, setUrl] = useState('');
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [selectedSourceId, setSelectedSourceId] = useState<number>(0);
  const [showCopiedAlertUrl, setShowCopiedAlertUrl] = useState(false);
  const [showCopiedAlertText, setShowCopiedAlertText] = useState(false);
  const navigate = useNavigate();

  const createFromUrl = useCreateLetterFromUrl();
  const createFromText = useCreateLetterFromText();
  const { data: cvOptions, isLoading: isLoadingOptions, error: optionsError } = useCVOptions();

  const handleUrlSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    createFromUrl.mutate({ url, source_id: selectedSourceId });
  };

  const handleTextSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    createFromText.mutate({ name, description, source_id: selectedSourceId });
  };

  return (
    <Box maxW="800px" mx="auto" mt={8} p={4}>
      {onBack && (
        <Button
          onClick={()=>navigate('/my-cvs')}
          mb={4}
          variant="outline"
        >
          My CVs
        </Button>
      )}

      <Heading mb={4} textAlign="center">
        Cover Letter Generator
      </Heading>

      {isLoadingOptions && (
        <Box textAlign="center" mb={4}>
          <Spinner size="md" />
          <Text ml={2}>Loading CV options...</Text>
        </Box>
      )}

      {optionsError && (
        <Alert status="error" mb={4}>
          <AlertIcon />
          <AlertDescription>
            Failed to load CV options: {optionsError.message}
          </AlertDescription>
        </Alert>
      )}

      <Tabs variant="enclosed" defaultIndex={0}>
        <TabList>
          <Tab>From URL</Tab>
          <Tab>From Text</Tab>
        </TabList>

        <TabPanels>
          <TabPanel>
            <Card>
              <CardHeader>
                <Heading size="md">Create Letter from URL</Heading>
              </CardHeader>
              <CardBody>
                <form onSubmit={handleUrlSubmit}>
                  <VStack spacing={4}>
                    <FormControl isRequired>
                      <FormLabel>Select Resume</FormLabel>
                      <Select
                        placeholder="Choose your resume"
                        value={selectedSourceId}
                        onChange={(e) => setSelectedSourceId(Number(e.target.value))}
                        isDisabled={isLoadingOptions}
                      >
                        <OptionsList response={cvOptions} />
                      </Select>
                      <FormHelperText>
                        Select which resume to use for generating the cover letter
                      </FormHelperText>
                    </FormControl>

                    <FormControl isRequired>
                      <FormLabel>URL</FormLabel>
                      <Input
                        type="url"
                        placeholder="https://example.com/job-description"
                        value={url}
                        onChange={(e) => setUrl(e.target.value)}
                      />
                    </FormControl>

                    <Button
                      type="submit"
                      colorScheme="blue"
                      isLoading={createFromUrl.isPending}
                      loadingText="Creating..."
                      width="full"
                    >
                      Create Letter from URL
                    </Button>
                  </VStack>
                </form>

                {createFromUrl.isError && (
                  <Alert status="error" mt={4}>
                    <AlertIcon />
                    <AlertTitle>Error!</AlertTitle>
                    <AlertDescription>
                      {createFromUrl.error.message}
                    </AlertDescription>
                  </Alert>
                )}

                {createFromUrl.isSuccess && (
                  <>
                    <Alert status="success" mt={4}>
                      <AlertIcon />
                      <AlertTitle>Success!</AlertTitle>
                      <AlertDescription>
                        {createFromUrl.data.message}
                      </AlertDescription>
                    </Alert>
                    
                    {createFromUrl.data.data?.letter_content && (
                      <Box mt={4} p={4} borderWidth="1px" borderRadius="lg" bg="gray.50" position="relative">
                        <HStack justify="space-between" mb={2}>
                          <Heading size="sm">Generated Letter</Heading>
                          <IconButton
                            aria-label="Copy to clipboard"
                            icon={<span>📋</span>}
                            size="sm"
                            onClick={() => {
                              navigator.clipboard.writeText(createFromUrl.data.data?.letter_content || '');
                              setShowCopiedAlertUrl(true);
                              setTimeout(() => setShowCopiedAlertUrl(false), 3000);
                            }}
                            colorScheme="blue"
                          />
                        </HStack>
                        {showCopiedAlertUrl && (
                          <Alert status="info" borderRadius="md" position="absolute" top={4} left={4} right={4} zIndex={10} boxShadow="lg">
                            <AlertIcon />
                            <AlertDescription>Скопировано в буфер обмена</AlertDescription>
                          </Alert>
                        )}
                        <Box
                          mt={2}
                          p={4}
                          bg="white"
                          borderRadius="md"
                          maxH="400px"
                          overflowY="auto"
                          whiteSpace="pre-wrap"
                          fontSize="sm"
                        >
                          {createFromUrl.data.data.letter_content}
                        </Box>
                      </Box>
                    )}
                  </>
                )}
              </CardBody>
            </Card>
          </TabPanel>

          <TabPanel>
            <Card>
              <CardHeader>
                <Heading size="md">Create Letter from Text</Heading>
              </CardHeader>
              <CardBody>
                <form onSubmit={handleTextSubmit}>
                  <VStack spacing={4}>
                    <FormControl isRequired>
                      <FormLabel>Select Resume</FormLabel>
                      <Select
                        placeholder="Choose your resume"
                        value={selectedSourceId}
                        onChange={(e) => setSelectedSourceId(Number(e.target.value))}
                        isDisabled={isLoadingOptions}
                      >
                        <OptionsList response={cvOptions} />
                    
                      </Select>
                      <FormHelperText>
                        Select which resume to use for generating the cover letter
                      </FormHelperText>
                    </FormControl>

                    <FormControl isRequired>
                      <FormLabel>Название</FormLabel>
                      <Input
                        placeholder="Enter letter name"
                        value={name}
                        onChange={(e) => setName(e.target.value)}
                      />
                    </FormControl>

                    <FormControl isRequired>
                      <FormLabel>Описание</FormLabel>
                      <Textarea
                        placeholder="Enter letter description"
                        value={description}
                        onChange={(e) => setDescription(e.target.value)}
                        rows={4}
                      />
                    </FormControl>


                    <Button
                      type="submit"
                      colorScheme="green"
                      isLoading={createFromText.isPending}
                      loadingText="Creating..."
                      width="full"
                    >
                      Create Letter from Text
                    </Button>
                  </VStack>
                </form>

                {createFromText.isError && (
                  <Alert status="error" mt={4}>
                    <AlertIcon />
                    <AlertTitle>Error!</AlertTitle>
                    <AlertDescription>
                      {createFromText.error.message}
                    </AlertDescription>
                  </Alert>
                )}

                {createFromText.isSuccess && (
                  <>
                    <Alert status="success" mt={4}>
                      <AlertIcon />
                      <AlertTitle>Success!</AlertTitle>
                      <AlertDescription>
                        {createFromText.data.message}
                      </AlertDescription>
                    </Alert>
                    
                    {createFromText.data.data?.letter_content && (
                      <Box mt={4} p={4} borderWidth="1px" borderRadius="lg" bg="gray.50" position="relative">
                        <HStack justify="space-between" mb={2}>
                          <Heading size="sm">Generated Letter</Heading>
                          <IconButton
                            aria-label="Copy to clipboard"
                            icon={<span>📋</span>}
                            size="sm"
                            onClick={() => {
                              navigator.clipboard.writeText(createFromText.data.data?.letter_content || '');
                              setShowCopiedAlertText(true);
                              setTimeout(() => setShowCopiedAlertText(false), 3000);
                            }}
                            colorScheme="blue"
                          />
                        </HStack>
                        {showCopiedAlertText && (
                          <Alert status="info" borderRadius="md" position="absolute" top={4} left={4} right={4} zIndex={10} boxShadow="lg">
                            <AlertIcon />
                            <AlertDescription>Скопировано в буфер обмена</AlertDescription>
                          </Alert>
                        )}
                        <Box
                          mt={2}
                          p={4}
                          bg="white"
                          borderRadius="md"
                          maxH="400px"
                          overflowY="auto"
                          whiteSpace="pre-wrap"
                          fontSize="sm"
                        >
                          {createFromText.data.data.letter_content}
                        </Box>
                      </Box>
                    )}
                  </>
                )}
              </CardBody>
            </Card>
          </TabPanel>
        </TabPanels>
      </Tabs>
    </Box>
  );
};

export default LetterGenerator;
