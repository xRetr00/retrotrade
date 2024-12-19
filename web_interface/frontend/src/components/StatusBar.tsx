import React from 'react';
import {
  Box,
  HStack,
  Text,
  Badge,
} from '@chakra-ui/react';

interface StatusBarProps {
  status: 'running' | 'stopped' | 'error';
  isConnected: boolean;
}

const StatusBar: React.FC<StatusBarProps> = ({ status, isConnected }) => {
  const getStatusColor = (status: string): string => {
    switch (status) {
      case 'running':
        return 'green';
      case 'stopped':
        return 'yellow';
      case 'error':
        return 'red';
      default:
        return 'gray';
    }
  };

  return (
    <Box bg="white" py={2} px={4} borderBottom="1px" borderColor="gray.200">
      <HStack spacing={4}>
        <HStack>
          <Text fontWeight="medium">Status:</Text>
          <Badge colorScheme={getStatusColor(status)}>{status}</Badge>
        </HStack>
        <HStack>
          <Text fontWeight="medium">Connection:</Text>
          <Badge colorScheme={isConnected ? 'green' : 'red'}>
            {isConnected ? 'Connected' : 'Disconnected'}
          </Badge>
        </HStack>
      </HStack>
    </Box>
  );
};

export default StatusBar; 