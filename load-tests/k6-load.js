import http from 'k6/http';
import { check, sleep } from 'k6';

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';
const API_KEY = __ENV.API_KEY || 'change-me';

const PROMPTS = [
  'Explain Kubernetes in one sentence.',
  'What is a container? Answer in two sentences.',
  'Write a 50-word explanation of GitOps.',
  'Why do teams use Helm? Keep it short.',
  'Explain the difference between latency and throughput.',
];

export const options = {
  // Ramp up concurrency in steps to find where the service saturates
  stages: [
    { duration: '1m', target: 1 },
    { duration: '1m', target: 3 },
    { duration: '1m', target: 6 },
    { duration: '1m', target: 10 },
    { duration: '30s', target: 0 },
  ],
  thresholds: {
    http_req_failed: ['rate<0.05'],
    http_req_duration: ['p(95)<5000'],
  },
  summaryTrendStats: ['avg', 'min', 'med', 'p(90)', 'p(95)', 'p(99)', 'max'],
};

export default function () {
  const prompt = PROMPTS[Math.floor(Math.random() * PROMPTS.length)];

  const res = http.post(
    `${BASE_URL}/v1/generate`,
    JSON.stringify({ prompt: prompt }),
    {
      headers: {
        'Content-Type': 'application/json',
        'X-API-Key': API_KEY,
      },
      timeout: '60s',
    }
  );

  check(res, {
    'status is 200': (r) => r.status === 200,
    'has response text': (r) => r.status === 200 && r.json('response') !== '',
  });

  sleep(0.2);
}