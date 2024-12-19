import React, { useState, useEffect } from 'react';
import {
  Box,
  VStack,
  HStack,
  Select,
  Stat,
  StatLabel,
  StatNumber,
  StatHelpText,
  StatArrow,
} from '@chakra-ui/react';
import { Line } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
} from 'chart.js';

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend
);

type ChartData = {
  labels: string[];
  values: number[];
};

type PerformanceData = {
  total_pnl: number;
  monthly_return: number;
  win_rate: number;
  chart_data: ChartData;
};

const defaultPerformance: PerformanceData = {
  total_pnl: 0,
  monthly_return: 0,
  win_rate: 0,
  chart_data: {
    labels: [],
    values: [],
  }
};

const defaultChartData = {
  labels: [],
  datasets: [
    {
      label: 'Portfolio Value',
      data: [],
      borderColor: 'rgb(75, 192, 192)',
      tension: 0.1,
    },
  ],
};

const PerformanceChart = () => {
  const [timeframe, setTimeframe] = useState('1d');
  const [performance, setPerformance] = useState<PerformanceData>(() => ({...defaultPerformance}));
  const [performanceData] = useState(defaultChartData);

  const options = {
    responsive: true,
    plugins: {
      legend: {
        position: 'top' as const,
      },
      title: {
        display: true,
        text: 'Portfolio Performance',
      },
    },
    scales: {
      y: {
        beginAtZero: false,
      },
    },
  };

  useEffect(() => {
    // Add your data fetching logic here
    // When data is fetched, update the performance state
    setPerformance({...defaultPerformance});
  }, [timeframe]);

  // Helper function to format numbers with 2 decimal places
  const formatNumber = (num: number) => {
    return num.toFixed(2);
  };

  // Helper function to determine color based on value
  const getPnLColor = (value: number) => {
    return value >= 0 ? 'green.500' : 'red.500';
  };

  // Helper function to determine StatArrow type
  const getArrowType = (value: number): 'increase' | 'decrease' => {
    return value >= 0 ? 'increase' : 'decrease';
  };

  const renderStat = (label: string, value: number, showArrow = true) => {
    const color = getPnLColor(value);
    const arrowType = getArrowType(value);
    const formattedValue = formatNumber(value);

    return (
      <Stat key={label}>
        <StatLabel>{label}</StatLabel>
        <StatNumber color={color}>
          {formattedValue}%
        </StatNumber>
        {showArrow ? (
          <StatHelpText>
            <StatArrow type={arrowType} />
            {label === 'Total PnL' ? 'Since inception' : 'This month'}
          </StatHelpText>
        ) : (
          <StatHelpText>Last 100 trades</StatHelpText>
        )}
      </Stat>
    );
  };

  // Ensure performance values are numbers
  const total_pnl = performance.total_pnl;
  const monthly_return = performance.monthly_return;
  const win_rate = performance.win_rate;

  return (
    <Box>
      <VStack spacing={6} align="stretch">
        <HStack spacing={8} justify="space-between">
          <Select
            value={timeframe}
            onChange={(e) => setTimeframe(e.target.value)}
            width="200px"
          >
            <option value="1d">1 Day</option>
            <option value="1w">1 Week</option>
            <option value="1m">1 Month</option>
            <option value="3m">3 Months</option>
            <option value="1y">1 Year</option>
          </Select>

          <HStack spacing={8}>
            {renderStat('Total PnL', total_pnl)}
            {renderStat('Monthly Return', monthly_return)}
            {renderStat('Win Rate', win_rate, false)}
          </HStack>
        </HStack>

        <Box height="400px">
          <Line options={options} data={performanceData} />
        </Box>
      </VStack>
    </Box>
  );
};

export default PerformanceChart;
