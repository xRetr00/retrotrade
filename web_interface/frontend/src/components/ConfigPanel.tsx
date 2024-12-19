import React, { useState } from 'react';
import {
  Box,
  VStack,
  FormControl,
  FormLabel,
  Input,
  Select,
  Button,
  useToast,
} from '@chakra-ui/react';

interface Config {
  risk_level: string;
  max_position_size: number;
  stop_loss_pct: number;
  take_profit_pct: number;
}

const defaultConfig: Config = {
  risk_level: 'medium',
  max_position_size: 1000,
  stop_loss_pct: 2,
  take_profit_pct: 4,
};

const ConfigPanel: React.FC = () => {
  const [config, setConfig] = useState<Config>(defaultConfig);
  const toast = useToast();

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    // Here you would typically send the config to your backend
    toast({
      title: 'Configuration Updated',
      description: 'Your trading configuration has been updated.',
      status: 'success',
      duration: 3000,
      isClosable: true,
    });
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const { name, value } = e.target;
    setConfig(prev => ({
      ...prev,
      [name]: name === 'risk_level' ? value : Number(value),
    }));
  };

  return (
    <Box p={4} borderWidth="1px" borderRadius="lg" bg="white" mb={4}>
      <form onSubmit={handleSubmit}>
        <VStack spacing={4} align="stretch">
          <FormControl>
            <FormLabel>Risk Level</FormLabel>
            <Select
              name="risk_level"
              value={config.risk_level}
              onChange={handleChange}
            >
              <option value="low">Low</option>
              <option value="medium">Medium</option>
              <option value="high">High</option>
            </Select>
          </FormControl>

          <FormControl>
            <FormLabel>Max Position Size</FormLabel>
            <Input
              name="max_position_size"
              type="number"
              value={config.max_position_size}
              onChange={handleChange}
            />
          </FormControl>

          <FormControl>
            <FormLabel>Stop Loss (%)</FormLabel>
            <Input
              name="stop_loss_pct"
              type="number"
              step="0.1"
              value={config.stop_loss_pct}
              onChange={handleChange}
            />
          </FormControl>

          <FormControl>
            <FormLabel>Take Profit (%)</FormLabel>
            <Input
              name="take_profit_pct"
              type="number"
              step="0.1"
              value={config.take_profit_pct}
              onChange={handleChange}
            />
          </FormControl>

          <Button type="submit" colorScheme="blue">
            Update Configuration
          </Button>
        </VStack>
      </form>
    </Box>
  );
};

export default ConfigPanel; 