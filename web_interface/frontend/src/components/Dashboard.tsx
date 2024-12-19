import React, { useState, useEffect } from 'react';
import {
  Box,
  Grid,
  GridItem,
  useColorModeValue,
  Text,
  VStack,
  HStack,
  Badge,
} from '@chakra-ui/react';
import { useWebSocket } from '../contexts/WebSocketContext';

interface Trade {
  id: string;
  symbol: string;
  side: 'buy' | 'sell';
  price: number;
  quantity: number;
  timestamp: string;
  pnl?: number;
}

const Dashboard: React.FC = () => {
  const [recentTrades, setRecentTrades] = useState<Trade[]>([]);
  const [pnlHistory, setPnlHistory] = useState<number[]>([]);
  const { socket, isConnected } = useWebSocket();

  const bgColor = useColorModeValue('white', 'gray.700');
  const textColor = useColorModeValue('gray.600', 'gray.200');

  useEffect(() => {
    if (socket && isConnected) {
      socket.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          switch (data.type) {
            case 'trade':
              setRecentTrades(prev => [...prev, data.trade].slice(-10));
              break;
            case 'pnl_update':
              setPnlHistory(prev => [...prev, data.pnl].slice(-100));
              break;
            default:
              break;
          }
        } catch (error) {
          console.error('Error parsing WebSocket message:', error);
        }
      };
    }
  }, [socket, isConnected]);

  return (
    <Box p={4}>
      <Grid templateColumns="repeat(12, 1fr)" gap={4}>
        <GridItem colSpan={8}>
          <Box bg={bgColor} p={4} borderRadius="lg" shadow="sm">
            <Text fontSize="lg" fontWeight="bold" mb={4}>Recent Trades</Text>
            <VStack spacing={3} align="stretch">
              {recentTrades.map((trade) => (
                <Box key={trade.id} p={3} borderWidth="1px" borderRadius="md">
                  <HStack justify="space-between">
                    <Text fontWeight="medium">{trade.symbol}</Text>
                    <Badge colorScheme={trade.side === 'buy' ? 'green' : 'red'}>
                      {trade.side.toUpperCase()}
                    </Badge>
                    <Text>{trade.quantity}</Text>
                    <Text>{trade.price}</Text>
                    {trade.pnl !== undefined && (
                      <Text color={trade.pnl >= 0 ? 'green.500' : 'red.500'}>
                        {trade.pnl.toFixed(2)}%
                      </Text>
                    )}
                  </HStack>
                </Box>
              ))}
              {recentTrades.length === 0 && (
                <Text color={textColor} textAlign="center">
                  No recent trades
                </Text>
              )}
            </VStack>
          </Box>
        </GridItem>

        <GridItem colSpan={4}>
          <Box bg={bgColor} p={4} borderRadius="lg" shadow="sm">
            <Text fontSize="lg" fontWeight="bold" mb={4}>Performance Summary</Text>
            <VStack spacing={3} align="stretch">
              <HStack justify="space-between">
                <Text>Total PnL</Text>
                <Text color={pnlHistory[pnlHistory.length - 1] >= 0 ? 'green.500' : 'red.500'}>
                  {pnlHistory[pnlHistory.length - 1]?.toFixed(2) || '0.00'}%
                </Text>
              </HStack>
              <HStack justify="space-between">
                <Text>Win Rate</Text>
                <Text>
                  {pnlHistory.length > 0
                    ? ((pnlHistory.filter(pnl => pnl >= 0).length / pnlHistory.length) * 100).toFixed(1)
                    : '0.0'}%
                </Text>
              </HStack>
            </VStack>
          </Box>
        </GridItem>
      </Grid>
    </Box>
  );
};

export default Dashboard; 