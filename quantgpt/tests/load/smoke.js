import http from "k6/http";
import { check, sleep } from "k6";

export const options = {
  scenarios: { health: { executor: "constant-vus", vus: 10, duration: "30s" } },
  thresholds: { http_req_failed: ["rate<0.01"], http_req_duration: ["p(95)<500"] },
};

const baseUrl = __ENV.BASE_URL || "http://localhost:8000";

export default function () {
  const response = http.get(`${baseUrl}/api/v1/health`);
  check(response, { "health is 200": (r) => r.status === 200 });
  sleep(0.2);
}
