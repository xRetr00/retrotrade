import React, { useState, useEffect } from 'react';
import {
  Box,
  VStack,
  Text,
  useToast,
} from '@chakra-ui/react';
import { useWebSocket } from '../contexts/WebSocketContext';

interface Position {
  symbol: string;
  side: 'long' | 'short';
  size: number;
  entry_price: number;
  current_price: number;
  pnl: number;
  pnl_percent: number;
}

const TradePanel: React.FC = () => {
  const [positions, setPositions] = useState<Position[]>([]);
  const { socket, isConnected } = useWebSocket();
  const toast = useToast();

  useEffect(() => {
    if (socket && isConnected) {
      // Listen for position updates
      socket.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.type === 'positions') {
            setPositions(data.positions);
            toast({
              title: 'Positions Updated',
              status: 'success',
              duration: 3000,
              isClosable: true,
            });
          }
        } catch (error) {
          console.error('Error parsing position data:', error);
          toast({
            title: 'Error',
            description: 'Failed to update positions',
            status: 'error',
            duration: 3000,
            isClosable: true,
          });
        }
      };
    }
  }, [socket, isConnected, toast]);

  return (
    <Box p={4} borderWidth="1px" borderRadius="lg">
      <VStack spacing={4} align="stretch">
        <Text fontSize="xl" fontWeight="bold">Active Positions</Text>
        {!isConnected && (
          <Text color="red.500">Disconnected from server</Text>
        )}
        {isConnected && positions.length === 0 ? (
          <Text>No active positions</Text>
        ) : (
          positions.map((position) => (
            <Box key={position.symbol} p={2} borderWidth="1px" borderRadius="md">
              <Text>{position.symbol}</Text>
              <Text>Side: {position.side}</Text>
              <Text>Size: {position.size}</Text>
              <Text>PnL: {position.pnl.toFixed(2)} ({position.pnl_percent.toFixed(2)}%)</Text>
            </Box>
          ))
        )}
      </VStack>
    </Box>
  );
};

export default TradePanel; 