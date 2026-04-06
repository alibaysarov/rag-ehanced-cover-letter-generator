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
  HStack,
} from '@chakra-ui/react';
import { CloseIcon } from '@chakra-ui/icons';
import { useCreateLetterFromUrl, useCreateLetterFromText, useCVOptions, useStreamLetter } from '@/hooks/useLetter';
import type { CVOptionsResponse } from '@/types/letter';
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
  const [showCopiedAlert, setShowCopiedAlert] = useState(false);
  const navigate = useNavigate();

  const createFromUrl = useCreateLetterFromUrl();
  const createFromText = useCreateLetterFromText();
  const { data: cvOptions, isLoading: isLoadingOptions, error: optionsError } = useCVOptions();
  const {
    content: streamContent,
    status: streamStatus,
    error: streamError,
    streamFromUrl,
    streamFromText,
    reset: resetStream,
  } = useStreamLetter();

  void createFromUrl;
  void createFromText;

  const isStreaming = streamStatus === 'parsing' || streamStatus === 'streaming';

  const handleUrlSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    streamFromUrl({ url, source_id: selectedSourceId });
  };

  const handleTextSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    streamFromText({ name, description, source_id: selectedSourceId });
  };

  return (
    <Box
      w="full"
      maxW={{ base: '100%', sm: '640px', md: '860px', lg: '1080px', xl: '1200px' }}
      mx="auto"
      mt={8}
      py="2"
      px={{ base: 4, md: 8 }}
    >
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
                      isLoading={isStreaming}
                      isDisabled={isStreaming || !url || !selectedSourceId}
                      loadingText="Creating..."
                      width="full"
                    >
                      Create Letter from URL
                    </Button>
                  </VStack>
                </form>
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
                      isLoading={isStreaming}
                      isDisabled={isStreaming || !name || !description || !selectedSourceId}
                      loadingText="Creating..."
                      width="full"
                    >
                      Create Letter from Text
                    </Button>
                  </VStack>
                </form>
              </CardBody>
            </Card>
          </TabPanel>
        </TabPanels>
      </Tabs>

      {/* Streaming Status & Result */}
      {streamStatus === 'parsing' && (
        <Card mt={6}>
          <CardBody>
            <HStack>
              <Spinner size="sm" />
              <Text>Analysing job post...</Text>
            </HStack>
          </CardBody>
        </Card>
      )}

      {streamError && (
        <Alert status="error" mt={6}>
          <AlertIcon />
          <AlertTitle>Error</AlertTitle>
          <AlertDescription>{streamError}</AlertDescription>
        </Alert>
      )}

      {(streamStatus === 'streaming' || streamStatus === 'done') && streamContent && (
        <Card mt={6}>
          <CardHeader>
            <HStack justifyContent="space-between">
              <Heading size="md">Generated Cover Letter</Heading>
              <HStack>
                {streamStatus === 'streaming' && (
                  <Button
                    size="sm"
                    colorScheme="red"
                    variant="outline"
                    leftIcon={<CloseIcon />}
                    onClick={resetStream}
                  >
                    Stop
                  </Button>
                )}
                <Button
                  size="sm"
                  colorScheme="blue"
                  isDisabled={streamStatus !== 'done'}
                  onClick={() => {
                    navigator.clipboard.writeText(streamContent);
                    setShowCopiedAlert(true);
                    setTimeout(() => setShowCopiedAlert(false), 2000);
                  }}
                >
                  Copy
                </Button>
              </HStack>
            </HStack>
          </CardHeader>
          <CardBody>
            <Box whiteSpace="pre-wrap" p={4} bg="gray.50" borderRadius="md" minH="200px">
              {streamContent}
              {streamStatus === 'streaming' && <Spinner size="xs" ml={1} />}
            </Box>
          </CardBody>
        </Card>
      )}

      {showCopiedAlert && (
        <Alert status="success" mt={4}>
          <AlertIcon />
          Copied to clipboard!
        </Alert>
      )}
    </Box>
  );
};

export default LetterGenerator;
