import React from 'react';
import { ChakraProvider, Box, Grid, GridItem } from '@chakra-ui/react';
import { WebSocketProvider } from './contexts/WebSocketContext';
import theme from './theme';
import StatusBar from './components/StatusBar';
import TradePanel from './components/TradePanel';
import ConfigPanel from './components/ConfigPanel';
import LogViewer from './components/LogViewer';
import PerformanceChart from './components/PerformanceChart';

const App: React.FC = () => {
  return (
    <ChakraProvider theme={theme}>
      <WebSocketProvider>
        <Box minH="100vh" bg="gray.50">
          <StatusBar status="running" isConnected={true} />
          <Grid
            templateColumns="repeat(12, 1fr)"
            gap={4}
            p={4}
          >
            <GridItem colSpan={8}>
              <PerformanceChart />
              <TradePanel />
            </GridItem>
            <GridItem colSpan={4}>
              <ConfigPanel />
              <LogViewer />
            </GridItem>
          </Grid>
        </Box>
      </WebSocketProvider>
    </ChakraProvider>
  );
};

export default App; 