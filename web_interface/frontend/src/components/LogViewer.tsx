import React, { useState, useEffect } from 'react';
import {
  Box,
  VStack,
  Text,
  Select,
  Badge,
} from '@chakra-ui/react';

interface LogEntry {
  timestamp: string;
  level: 'info' | 'warning' | 'error';
  message: string;
}

const LogViewer: React.FC = () => {
  const [logLevel, setLogLevel] = useState<string>('all');
  const [logs, setLogs] = useState<LogEntry[]>([]);

  useEffect(() => {
    // Simulated log data - replace with actual WebSocket data
    const demoLogs: LogEntry[] = [
      {
        timestamp: new Date().toISOString(),
        level: 'info',
        message: 'System initialized successfully',
      },
      {
        timestamp: new Date().toISOString(),
        level: 'warning',
        message: 'High volatility detected',
      },
    ];
    setLogs(demoLogs);
  }, []);

  const getLevelColor = (level: string): string => {
    switch (level) {
      case 'error':
        return 'red';
      case 'warning':
        return 'yellow';
      case 'info':
        return 'blue';
      default:
        return 'gray';
    }
  };

  const filteredLogs = logLevel === 'all'
    ? logs
    : logs.filter(log => log.level === logLevel);

  return (
    <Box p={4} borderWidth="1px" borderRadius="lg" bg="white">
      <VStack spacing={4} align="stretch">
        <Select
          value={logLevel}
          onChange={(e) => setLogLevel(e.target.value)}
          mb={2}
        >
          <option value="all">All Levels</option>
          <option value="info">Info</option>
          <option value="warning">Warning</option>
          <option value="error">Error</option>
        </Select>

        <Box
          maxHeight="300px"
          overflowY="auto"
          borderWidth="1px"
          borderRadius="md"
          p={2}
        >
          {filteredLogs.map((log, index) => (
            <Box
              key={index}
              p={2}
              borderBottomWidth={index < filteredLogs.length - 1 ? 1 : 0}
            >
              <Text fontSize="sm" color="gray.500">
                {new Date(log.timestamp).toLocaleString()}
              </Text>
              <Text display="flex" alignItems="center" gap={2}>
                <Badge colorScheme={getLevelColor(log.level)}>
                  {log.level.toUpperCase()}
                </Badge>
                {log.message}
              </Text>
            </Box>
          ))}
          {filteredLogs.length === 0 && (
            <Text color="gray.500" textAlign="center" py={4}>
              No logs to display
            </Text>
          )}
        </Box>
      </VStack>
    </Box>
  );
};

export default LogViewer; 