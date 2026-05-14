import React from 'react';
import {
  Box,
  Card,
  CardBody,
  FormControl,
  FormErrorMessage,
  FormLabel,
  Heading,
  HStack,
  IconButton,
  Input,
  VStack,
} from '@chakra-ui/react';
import { CloseIcon } from '@chakra-ui/icons';
import AnimatedListInput from './AnimatedListInput';

export interface ProjectInput {
  name: string;
  skills: string[];
  achievements: string[];
  technologies: string[];
}

export const emptyProject = (): ProjectInput => ({
  name: '',
  skills: [],
  achievements: [],
  technologies: [],
});

interface ProjectFormCardProps {
  value: ProjectInput;
  onChange: (next: ProjectInput) => void;
  onRemove?: () => void;
  index?: number;
  nameError?: string;
}

const ProjectFormCard: React.FC<ProjectFormCardProps> = ({
  value,
  onChange,
  onRemove,
  index,
  nameError,
}) => {
  const update = <K extends keyof ProjectInput>(key: K, v: ProjectInput[K]) => {
    onChange({ ...value, [key]: v });
  };

  return (
    <Card variant="outline">
      <CardBody>
        <HStack justify="space-between" mb={3} align="start">
          <Heading size="sm">
            {typeof index === 'number' ? `Проект #${index + 1}` : 'Проект'}
          </Heading>
          {onRemove && (
            <IconButton
              aria-label="Удалить проект"
              icon={<CloseIcon boxSize={3} />}
              size="sm"
              variant="ghost"
              colorScheme="red"
              onClick={onRemove}
            />
          )}
        </HStack>
        <VStack spacing={4} align="stretch">
          <FormControl isInvalid={!!nameError} isRequired>
            <FormLabel>Название</FormLabel>
            <Input
              value={value.name}
              onChange={(e) => update('name', e.target.value)}
              placeholder="LOKALI APP"
            />
            <FormErrorMessage>{nameError}</FormErrorMessage>
          </FormControl>

          <Box>
            <AnimatedListInput
              label="Навыки (skills)"
              values={value.skills}
              onChange={(v) => update('skills', v)}
              placeholder="проектирование REST API"
            />
          </Box>

          <Box>
            <AnimatedListInput
              label="Достижения (achievements)"
              values={value.achievements}
              onChange={(v) => update('achievements', v)}
              placeholder="Создал REST API для мобильного приложения"
            />
          </Box>

          <Box>
            <AnimatedListInput
              label="Технологии (technologies)"
              values={value.technologies}
              onChange={(v) => update('technologies', v)}
              placeholder="Node.js"
            />
          </Box>
        </VStack>
      </CardBody>
    </Card>
  );
};

export default ProjectFormCard;
