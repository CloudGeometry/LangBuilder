# Performance Testing Guide

## Overview

This document provides comprehensive guidance for performance testing LangBuilder v1.6.5, a visual AI workflow builder with FastAPI backend and React frontend. Performance testing ensures the platform meets scalability requirements, identifies bottlenecks, and validates that system behavior under load matches production expectations.

## Performance Testing Strategy

### Goals

1. **Establish Baseline Metrics**: Define current performance characteristics across all system components
2. **Identify Bottlenecks**: Pinpoint performance constraints in API, database, workflow execution, and frontend rendering
3. **Validate SLAs**: Ensure the system meets defined service level agreements under expected and peak loads
4. **Prevent Regressions**: Detect performance degradation in CI/CD pipelines before production deployment
5. **Optimize Resource Usage**: Balance performance with infrastructure costs for Docker, Celery workers, and message brokers

### Target SLAs

| Metric | Target | Critical Threshold |
|--------|--------|-------------------|
| API Response Time (p95) | < 500ms | < 1000ms |
| API Response Time (p99) | < 1000ms | < 2000ms |
| Workflow Execution (simple) | < 2s | < 5s |
| Workflow Execution (complex) | < 10s | < 30s |
| WebSocket Message Latency | < 100ms | < 300ms |
| Frontend Canvas Render (100 nodes) | < 1s | < 2s |
| Database Query Time (p95) | < 100ms | < 250ms |
| Concurrent Users Supported | 100+ | 50+ |
| Throughput (requests/sec) | 50+ | 20+ |

### Baseline Metrics

Establish baselines for:

- **API Endpoints**: Response time distribution, throughput, error rates
- **Database**: Query execution time, connection pool utilization, lock contention
- **Workflow Engine**: LangChain graph execution time, memory consumption per workflow
- **WebSocket Connections**: Concurrent connections supported, message throughput
- **Frontend**: Initial load time, canvas rendering time, bundle size
- **Infrastructure**: CPU/memory utilization, container resource usage, Celery task queue depth

## Load Testing

### Overview

Load testing validates system behavior under expected and peak user loads. Focus on the 157 API endpoints, particularly high-traffic endpoints that serve workflow execution and chat operations.

### Key Endpoints for Load Testing

| Endpoint | Purpose | Expected Load | Critical Path |
|----------|---------|--------------|---------------|
| `/api/v1/flows` | Flow CRUD operations | Medium | Yes |
| `/api/v1/build` | Chat/build operations | High | Yes |
| `/api/v1/run/{flow_id}` | Workflow execution | High | Yes |
| `/v1/chat/completions` | OpenAI-compatible chat | High | Yes |
| `/api/v1/projects` | Project management | Medium | No |
| `/api/v1/mcp` | MCP protocol | Low | No |
| `/health` | Health checks | Very High | No |
| `/api/v1/files` | File operations | Medium | No |

### Tool: Locust

LangBuilder includes Locust configuration at `langbuilder/src/backend/tests/locust/locustfile.py`.

#### Running Locust Tests

**Basic load test:**

```bash
cd langbuilder/src/backend/tests/locust

# Set required environment variables
export API_KEY="your-api-key"
export LANGBUILDER_HOST="http://localhost:8002"
export FLOW_ID="your-flow-uuid"

# Run with 50 users, spawn rate 5/sec, 5-minute test
locust -f locustfile.py --users 50 --spawn-rate 5 --run-time 5m --headless
```

**With custom configuration:**

```bash
# Adjust wait times and timeout
export MIN_WAIT=1000  # 1 second minimum wait
export MAX_WAIT=3000  # 3 seconds maximum wait
export REQUEST_TIMEOUT=30.0  # 30 second timeout

locust -f locustfile.py \
    --users 100 \
    --spawn-rate 10 \
    --run-time 10m \
    --headless \
    --html=report.html
```

**Web UI mode:**

```bash
locust -f locustfile.py --host=http://localhost:8002
# Open http://localhost:8089 in browser
```

#### Extending Locust Tests

The existing `FlowRunUser` class tests `/api/v1/run/{flow_id}`. Add additional task classes for comprehensive coverage:

```python
# locustfile.py

from locust import HttpUser, between, task
import os

class FlowManagementUser(HttpUser):
    """Test flow CRUD operations."""

    wait_time = between(1, 3)
    host = os.getenv("LANGBUILDER_HOST", "http://localhost:8002")

    def on_start(self):
        """Authenticate and setup."""
        self.api_key = os.getenv("API_KEY")
        if not self.api_key:
            raise ValueError("API_KEY required")

    @task(3)
    def list_flows(self):
        """GET /api/v1/flows - List all flows."""
        headers = {"x-api-key": self.api_key}
        with self.client.get("/api/v1/flows", headers=headers, catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Got status code {response.status_code}")

    @task(1)
    def create_flow(self):
        """POST /api/v1/flows - Create new flow."""
        headers = {"x-api-key": self.api_key, "Content-Type": "application/json"}
        payload = {
            "name": "Load Test Flow",
            "description": "Generated by Locust",
            "data": {"nodes": [], "edges": []}
        }
        with self.client.post("/api/v1/flows", json=payload, headers=headers, catch_response=True) as response:
            if response.status_code in [200, 201]:
                response.success()
            else:
                response.failure(f"Got status code {response.status_code}")


class ChatCompletionUser(HttpUser):
    """Test OpenAI-compatible endpoint."""

    wait_time = between(2, 5)
    host = os.getenv("LANGBUILDER_HOST", "http://localhost:8002")

    def on_start(self):
        self.api_key = os.getenv("API_KEY")
        if not self.api_key:
            raise ValueError("API_KEY required")

    @task
    def chat_completion(self):
        """POST /v1/chat/completions - OpenAI-compatible chat."""
        headers = {"x-api-key": self.api_key, "Content-Type": "application/json"}
        payload = {
            "model": "test-flow",
            "messages": [{"role": "user", "content": "Hello, how are you?"}],
            "stream": False
        }
        with self.client.post("/v1/chat/completions", json=payload, headers=headers, catch_response=True, timeout=30) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Got status code {response.status_code}")
```

### Tool: k6

Alternative to Locust for JavaScript-based load testing:

#### Installation

```bash
# Ubuntu/Debian
sudo gpg -k
sudo gpg --no-default-keyring --keyring /usr/share/keyrings/k6-archive-keyring.gpg --keyserver hkp://keyserver.ubuntu.com:80 --recv-keys C5AD17C747E3415A3642D57D77C6C491D6AC1D69
echo "deb [signed-by=/usr/share/keyrings/k6-archive-keyring.gpg] https://dl.k6.io/deb stable main" | sudo tee /etc/apt/sources.list.d/k6.list
sudo apt-get update
sudo apt-get install k6

# macOS
brew install k6
```

#### k6 Test Script Example

**File:** `langbuilder/src/backend/tests/k6/flow-execution.js`

```javascript
import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate } from 'k6/metrics';

const errorRate = new Rate('errors');

export const options = {
  stages: [
    { duration: '2m', target: 10 },   // Ramp up to 10 users
    { duration: '5m', target: 50 },   // Stay at 50 users
    { duration: '2m', target: 100 },  // Spike to 100 users
    { duration: '5m', target: 100 },  // Stay at 100 users
    { duration: '2m', target: 0 },    // Ramp down to 0
  ],
  thresholds: {
    http_req_duration: ['p(95)<500', 'p(99)<1000'],
    http_req_failed: ['rate<0.01'],
    errors: ['rate<0.05'],
  },
};

const API_KEY = __ENV.API_KEY;
const BASE_URL = __ENV.LANGBUILDER_HOST || 'http://localhost:8002';
const FLOW_ID = __ENV.FLOW_ID;

export default function () {
  const headers = {
    'x-api-key': API_KEY,
    'Content-Type': 'application/json',
  };

  const payload = JSON.stringify({
    input_value: 'What is the weather today?',
    output_type: 'chat',
    input_type: 'chat',
    tweaks: {},
  });

  const res = http.post(
    `${BASE_URL}/api/v1/run/${FLOW_ID}?stream=false`,
    payload,
    { headers, timeout: '30s' }
  );

  const success = check(res, {
    'status is 200': (r) => r.status === 200,
    'response time < 1000ms': (r) => r.timings.duration < 1000,
    'has valid JSON': (r) => {
      try {
        JSON.parse(r.body);
        return true;
      } catch {
        return false;
      }
    },
  });

  errorRate.add(!success);
  sleep(1);
}
```

#### Running k6 Tests

```bash
export API_KEY="your-api-key"
export FLOW_ID="your-flow-uuid"
k6 run langbuilder/src/backend/tests/k6/flow-execution.js
```

### Concurrent User Simulation

Test realistic user behavior patterns:

1. **Read-Heavy Pattern** (80% reads, 20% writes):
   - 80% GET requests (list flows, get flow details)
   - 20% POST/PUT requests (create/update flows)

2. **Workflow Execution Pattern** (execution-focused):
   - 60% workflow runs
   - 30% flow reads
   - 10% flow updates

3. **Peak Load Pattern** (maximum sustained load):
   - Gradual ramp-up to 200 concurrent users
   - Sustained load for 15 minutes
   - Monitor for degradation

### Load Test Scenarios

| Scenario | Users | Duration | Purpose |
|----------|-------|----------|---------|
| Baseline | 1-10 | 5 min | Establish single-user and low-load baselines |
| Normal Load | 50 | 15 min | Validate typical production load |
| Peak Load | 100 | 30 min | Test maximum expected concurrent users |
| Stress Test | 200+ | Until failure | Find breaking point |
| Endurance | 50 | 4 hours | Detect memory leaks and resource exhaustion |

## Stress Testing

### Overview

Stress testing pushes the system beyond normal operating capacity to identify breaking points, resource limits, and failure modes.

### Breaking Point Identification

**Methodology:**

1. Start with baseline load (10 users)
2. Incrementally increase load by 25% every 5 minutes
3. Monitor key metrics:
   - Response time degradation (p95 > 2s = warning, p95 > 5s = critical)
   - Error rate increase (> 1% = warning, > 5% = critical)
   - CPU/memory saturation (> 80% = warning, > 95% = critical)
4. Identify the point where:
   - Response times exceed 5x baseline
   - Error rate exceeds 5%
   - System becomes unresponsive

**Locust stress test:**

```bash
# Progressive stress test
locust -f locustfile.py \
    --users 500 \
    --spawn-rate 50 \
    --run-time 30m \
    --headless \
    --html=stress-report.html
```

### Resource Exhaustion Scenarios

#### Database Connection Pool Exhaustion

**Test:** Saturate the database connection pool (default SQLite has limited concurrency).

```python
# stress_test_db_pool.py
import asyncio
import aiosqlite
from langbuilder.services.deps import get_settings_service

async def exhaust_connections():
    """Open connections until pool exhausted."""
    settings = get_settings_service()
    connections = []

    try:
        for i in range(200):
            conn = await aiosqlite.connect(settings.settings.database_url)
            connections.append(conn)
            print(f"Opened connection {i+1}")
            await asyncio.sleep(0.1)
    except Exception as e:
        print(f"Pool exhausted at {len(connections)} connections: {e}")
    finally:
        for conn in connections:
            await conn.close()

if __name__ == "__main__":
    asyncio.run(exhaust_connections())
```

**Expected behavior:**
- PostgreSQL: Pool size configurable (default 20-50)
- SQLite: Limited concurrent writes, expect failures around 10-20 concurrent connections

#### Memory Exhaustion

**Test:** Execute memory-intensive workflows until OOM.

```python
# stress_test_memory.py
import asyncio
from langbuilder.api.v1.run import run_flow

async def memory_stress_test():
    """Run memory-intensive workflows concurrently."""
    tasks = []

    # Create 50 concurrent large workflow executions
    for i in range(50):
        # Workflow that processes large datasets
        task = asyncio.create_task(run_flow_with_large_data())
        tasks.append(task)

    await asyncio.gather(*tasks, return_exceptions=True)

# Monitor: docker stats, prometheus memory metrics
```

#### Celery Queue Saturation

**Test:** Submit tasks faster than workers can process.

```bash
# Submit 1000 tasks rapidly
for i in {1..1000}; do
    curl -X POST http://localhost:8002/api/v1/run/{flow_id} \
        -H "x-api-key: ${API_KEY}" \
        -H "Content-Type: application/json" \
        -d '{"input_value": "test", "output_type": "chat"}' &
done

# Monitor RabbitMQ queue depth
docker exec rabbitmq rabbitmqctl list_queues
```

**Expected behavior:**
- Tasks queue in RabbitMQ
- Workers process at max capacity
- Graceful degradation (longer wait times, no errors)

### Recovery Behavior

Test system recovery after stress:

1. **Gradual Recovery Test:**
   - Apply 200% load for 5 minutes
   - Reduce to 50% load
   - Measure time to return to baseline performance

2. **Circuit Breaker Test:**
   - Trigger failure condition (e.g., database connection loss)
   - Verify circuit breaker opens
   - Restore service
   - Verify circuit breaker closes and traffic resumes

3. **Cascading Failure Prevention:**
   - Overload a dependency (e.g., Redis)
   - Verify the system doesn't cascade fail
   - Monitor timeout/retry behavior

## Frontend Performance

### Canvas Rendering Performance

Test React Flow canvas with varying node counts using the frontend test infrastructure.

#### React Flow Performance Test

**File:** `langbuilder/src/frontend/src/__tests__/performance/canvas-rendering.test.tsx`

```typescript
import { render, waitFor } from '@testing-library/react';
import { ReactFlowProvider } from '@xyflow/react';
import { FlowCanvas } from '@/components/FlowCanvas';
import { generateMockFlow } from '@/utils/test-helpers';

describe('Canvas Rendering Performance', () => {
  const testCases = [
    { nodes: 50, label: 'small flow' },
    { nodes: 100, label: 'medium flow' },
    { nodes: 500, label: 'large flow' },
  ];

  testCases.forEach(({ nodes, label }) => {
    it(`renders ${label} (${nodes} nodes) within acceptable time`, async () => {
      const mockFlow = generateMockFlow(nodes);
      const startTime = performance.now();

      const { container } = render(
        <ReactFlowProvider>
          <FlowCanvas flow={mockFlow} />
        </ReactFlowProvider>
      );

      await waitFor(() => {
        const allNodes = container.querySelectorAll('.react-flow__node');
        expect(allNodes.length).toBe(nodes);
      });

      const endTime = performance.now();
      const renderTime = endTime - startTime;

      console.log(`${label}: ${renderTime.toFixed(2)}ms`);

      // Performance assertions
      if (nodes <= 50) {
        expect(renderTime).toBeLessThan(500);
      } else if (nodes <= 100) {
        expect(renderTime).toBeLessThan(1000);
      } else if (nodes <= 500) {
        expect(renderTime).toBeLessThan(3000);
      }
    });
  });
});
```

**Run with:**

```bash
cd langbuilder/src/frontend
npm run test -- canvas-rendering.test.tsx
```

#### Manual Canvas Performance Testing

1. **Build development version:**
   ```bash
   cd langbuilder/src/frontend
   npm run dev
   ```

2. **Test scenarios:**
   - Open Chrome DevTools > Performance
   - Start recording
   - Load flow with 50/100/500 nodes
   - Stop recording and analyze:
     - Scripting time (React rendering)
     - Layout/Paint time
     - Total blocking time

3. **Metrics to track:**
   - First Contentful Paint (FCP)
   - Largest Contentful Paint (LCP)
   - Time to Interactive (TTI)
   - Total Blocking Time (TBT)

### Bundle Size Analysis

Monitor frontend bundle size to prevent bloat.

#### Analyze Bundle

```bash
cd langbuilder/src/frontend

# Build for production
npm run build

# Analyze bundle composition
npx vite-bundle-visualizer

# Check bundle size
ls -lh dist/assets/*.js
```

#### Bundle Size Targets

| Asset | Target | Warning | Critical |
|-------|--------|---------|----------|
| Main JS Bundle | < 500 KB | 750 KB | 1 MB |
| Main CSS Bundle | < 100 KB | 150 KB | 200 KB |
| Vendor Chunks | < 300 KB | 500 KB | 750 KB |
| Total (gzipped) | < 250 KB | 400 KB | 500 KB |

#### Optimization Strategies

1. **Code Splitting:** Lazy load routes and heavy components
2. **Tree Shaking:** Remove unused exports
3. **Vendor Chunking:** Split large dependencies
4. **Dynamic Imports:** Load components on demand

```typescript
// Example: Lazy load heavy component
const FlowCanvas = lazy(() => import('@/components/FlowCanvas'));

function App() {
  return (
    <Suspense fallback={<LoadingSpinner />}>
      <FlowCanvas />
    </Suspense>
  );
}
```

### Lighthouse Metrics Targets

Run Lighthouse CI in GitHub Actions or locally.

#### Lighthouse CI Configuration

**File:** `.lighthouserc.json`

```json
{
  "ci": {
    "collect": {
      "url": ["http://localhost:5175"],
      "startServerCommand": "npm run preview",
      "numberOfRuns": 3
    },
    "assert": {
      "preset": "lighthouse:recommended",
      "assertions": {
        "categories:performance": ["error", {"minScore": 0.9}],
        "categories:accessibility": ["error", {"minScore": 0.95}],
        "categories:best-practices": ["error", {"minScore": 0.9}],
        "categories:seo": ["error", {"minScore": 0.9}],
        "first-contentful-paint": ["error", {"maxNumericValue": 2000}],
        "largest-contentful-paint": ["error", {"maxNumericValue": 2500}],
        "cumulative-layout-shift": ["error", {"maxNumericValue": 0.1}],
        "total-blocking-time": ["error", {"maxNumericValue": 300}]
      }
    },
    "upload": {
      "target": "temporary-public-storage"
    }
  }
}
```

#### Run Lighthouse Locally

```bash
cd langbuilder/src/frontend

# Install Lighthouse CI
npm install -g @lhci/cli

# Run Lighthouse
lhci autorun
```

### React Rendering Performance

Use React DevTools Profiler to identify slow components.

#### Profiling Steps

1. **Enable Profiler:**
   ```bash
   # Development mode automatically enables profiler
   npm run dev
   ```

2. **Capture Profile:**
   - Open React DevTools > Profiler
   - Click "Record"
   - Perform actions (load flow, drag nodes, etc.)
   - Stop recording

3. **Analyze:**
   - Identify components with long render times
   - Look for unnecessary re-renders
   - Check for expensive calculations in render

#### Optimization Techniques

1. **Memoization:**
   ```typescript
   import { memo, useMemo, useCallback } from 'react';

   const FlowNode = memo(({ node }) => {
     const computedStyles = useMemo(() => calculateStyles(node), [node]);
     const handleClick = useCallback(() => selectNode(node.id), [node.id]);

     return <div style={computedStyles} onClick={handleClick}>{node.label}</div>;
   });
   ```

2. **Virtualization:** For long lists, use `react-window` or `react-virtualized`

3. **Debouncing:** Reduce update frequency for expensive operations
   ```typescript
   import { debounce } from 'lodash';

   const debouncedUpdate = useMemo(
     () => debounce((value) => updateFlow(value), 300),
     []
   );
   ```

## Database Performance

### Query Performance Benchmarks

#### Benchmark Key Queries

**File:** `langbuilder/src/backend/tests/performance/test_database_queries.py`

```python
import pytest
import time
from sqlmodel import select
from langbuilder.services.database.models.flow import Flow
from langbuilder.services.deps import get_session

@pytest.mark.asyncio
async def test_flow_list_query_performance():
    """Benchmark flow list query."""
    async with get_session() as session:
        start = time.perf_counter()

        statement = select(Flow).limit(100)
        result = await session.exec(statement)
        flows = result.all()

        elapsed = (time.perf_counter() - start) * 1000

        print(f"Query time: {elapsed:.2f}ms for {len(flows)} flows")
        assert elapsed < 100, f"Query took {elapsed}ms, expected < 100ms"

@pytest.mark.asyncio
async def test_flow_with_joins_performance():
    """Benchmark flow query with relationships."""
    async with get_session() as session:
        start = time.perf_counter()

        # Query flow with related data
        statement = select(Flow).where(Flow.id == "test-flow-id")
        result = await session.exec(statement)
        flow = result.first()

        # Access relationships (triggers additional queries if not eager-loaded)
        _ = flow.user
        _ = flow.folder

        elapsed = (time.perf_counter() - start) * 1000

        print(f"Query with joins: {elapsed:.2f}ms")
        assert elapsed < 200, f"Query took {elapsed}ms, expected < 200ms"
```

**Run benchmarks:**

```bash
cd langbuilder/src/backend
pytest tests/performance/test_database_queries.py -v -s
```

#### Query Performance Targets

| Query Type | Target | Warning | Critical |
|------------|--------|---------|----------|
| Simple SELECT | < 10ms | 50ms | 100ms |
| SELECT with JOIN | < 50ms | 150ms | 300ms |
| Complex aggregation | < 100ms | 300ms | 500ms |
| INSERT | < 20ms | 100ms | 200ms |
| UPDATE | < 30ms | 100ms | 200ms |
| DELETE | < 20ms | 100ms | 200ms |

### Connection Pool Tuning

#### PostgreSQL Connection Pool Configuration

**SQLModel/SQLAlchemy Configuration:**

```python
# langbuilder/services/database/connection.py

from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool, QueuePool

def create_engine(database_url: str, pool_size: int = 20, max_overflow: int = 10):
    """Create async database engine with optimized pool settings."""

    # Use NullPool for SQLite (no pooling needed)
    if database_url.startswith("sqlite"):
        return create_async_engine(
            database_url,
            poolclass=NullPool,
            echo=False,
            future=True,
        )

    # PostgreSQL with connection pooling
    return create_async_engine(
        database_url,
        poolclass=QueuePool,
        pool_size=pool_size,          # Persistent connections
        max_overflow=max_overflow,    # Additional connections if needed
        pool_timeout=30,              # Max wait time for connection
        pool_recycle=3600,            # Recycle connections after 1 hour
        pool_pre_ping=True,           # Verify connections before use
        echo=False,
        future=True,
    )
```

#### Recommended Pool Sizes

| Environment | Pool Size | Max Overflow | Total Max |
|-------------|-----------|--------------|-----------|
| Development | 5 | 5 | 10 |
| Staging | 20 | 10 | 30 |
| Production (small) | 20 | 20 | 40 |
| Production (large) | 50 | 50 | 100 |

**Formula:** `pool_size = (2 * number_of_cpu_cores) + effective_spindle_count`

For cloud databases, consider:
- Database max connections limit
- Number of application instances
- `connections_per_instance = (max_db_connections * 0.8) / num_app_instances`

#### Monitoring Connection Pool

```python
# Check pool statistics
from langbuilder.services.deps import get_db_engine

engine = get_db_engine()
pool = engine.pool

print(f"Pool size: {pool.size()}")
print(f"Checked in: {pool.checkedin()}")
print(f"Checked out: {pool.checkedout()}")
print(f"Overflow: {pool.overflow()}")
```

### Migration Performance

Test Alembic migration performance, especially for large datasets.

#### Benchmark Migration

```bash
# Create test database with sample data
python scripts/seed_test_data.py --flows 10000 --users 1000

# Time migration
time alembic upgrade head

# Measure:
# - Migration execution time
# - Database lock duration
# - Impact on running application
```

#### Migration Performance Guidelines

1. **Batch Operations:** Use batch mode for large table modifications
2. **Avoid Full Table Scans:** Create indexes before running queries
3. **Minimize Downtime:** Use techniques like:
   - Add new column (nullable)
   - Backfill data in batches
   - Add NOT NULL constraint
   - Drop old column

**Example: Efficient migration**

```python
# alembic/versions/xxx_add_column.py

from alembic import op
import sqlalchemy as sa

def upgrade():
    # Add nullable column (fast)
    op.add_column('flow', sa.Column('new_field', sa.String(), nullable=True))

    # Backfill in batches (not in migration, run separately)
    # op.execute("UPDATE flow SET new_field = 'default' WHERE new_field IS NULL")

    # Add constraint later after backfill
    # op.alter_column('flow', 'new_field', nullable=False)

def downgrade():
    op.drop_column('flow', 'new_field')
```

## Workflow Execution Performance

### LangChain Graph Execution Timing

#### Benchmark Workflow Execution

**File:** `langbuilder/src/backend/tests/performance/test_workflow_execution.py`

```python
import pytest
import time
from langbuilder.api.v1.run import run_flow

@pytest.mark.asyncio
async def test_simple_workflow_execution_time():
    """Benchmark simple LangChain workflow."""
    flow_id = "simple-llm-flow"

    start = time.perf_counter()

    result = await run_flow(
        flow_id=flow_id,
        input_value="Hello, world!",
        output_type="chat",
    )

    elapsed = (time.perf_counter() - start) * 1000

    print(f"Simple workflow: {elapsed:.2f}ms")
    assert elapsed < 2000, f"Workflow took {elapsed}ms, expected < 2s"

@pytest.mark.asyncio
async def test_complex_workflow_execution_time():
    """Benchmark complex multi-node workflow."""
    flow_id = "complex-rag-flow"  # RAG with vector store, retrieval, LLM

    start = time.perf_counter()

    result = await run_flow(
        flow_id=flow_id,
        input_value="What is LangChain?",
        output_type="chat",
    )

    elapsed = (time.perf_counter() - start) * 1000

    print(f"Complex workflow: {elapsed:.2f}ms")
    assert elapsed < 10000, f"Workflow took {elapsed}ms, expected < 10s"
```

#### Workflow Performance Breakdown

Profile individual components in workflow:

```python
from langbuilder.graph.vertex import VertexNode
from langbuilder.utils.timing import profile_component

@profile_component
async def execute_node(node: VertexNode):
    """Execute node with timing."""
    result = await node.run()
    return result

# Output:
# Component: LLMComponent - 450ms
# Component: VectorStoreRetriever - 150ms
# Component: PromptTemplate - 5ms
```

### Streaming Response Latency

Measure time-to-first-token (TTFT) and inter-token latency.

#### Streaming Performance Test

**File:** `langbuilder/src/backend/tests/performance/test_streaming.py`

```python
import pytest
import time
import asyncio
from langbuilder.api.v1.run import run_flow_stream

@pytest.mark.asyncio
async def test_streaming_ttft():
    """Measure time to first token in streaming response."""
    flow_id = "streaming-flow"

    start = time.perf_counter()
    first_token_time = None
    token_times = []

    async for chunk in run_flow_stream(flow_id=flow_id, input_value="Tell me a story"):
        current_time = time.perf_counter()

        if first_token_time is None:
            first_token_time = (current_time - start) * 1000
            print(f"Time to first token: {first_token_time:.2f}ms")
        else:
            token_times.append((current_time - start) * 1000)

    # Assertions
    assert first_token_time < 500, f"TTFT {first_token_time}ms, expected < 500ms"

    if len(token_times) > 1:
        avg_inter_token = sum(token_times[i] - token_times[i-1] for i in range(1, len(token_times))) / (len(token_times) - 1)
        print(f"Average inter-token latency: {avg_inter_token:.2f}ms")
        assert avg_inter_token < 100, f"Inter-token latency {avg_inter_token}ms, expected < 100ms"
```

### Memory Usage During Complex Workflows

Monitor memory consumption to prevent OOM errors.

#### Memory Profiling

**Install memory_profiler:**

```bash
pip install memory-profiler
```

**Profile workflow execution:**

```python
# test_memory_profile.py
from memory_profiler import profile
from langbuilder.api.v1.run import run_flow

@profile
async def profile_workflow_memory():
    """Profile memory usage during workflow execution."""
    result = await run_flow(
        flow_id="large-workflow",
        input_value="Process large dataset",
    )
    return result

if __name__ == "__main__":
    import asyncio
    asyncio.run(profile_workflow_memory())
```

**Run:**

```bash
python -m memory_profiler test_memory_profile.py
```

**Expected output:**

```
Line    Mem usage    Increment   Line Contents
================================================
     3   45.5 MiB   45.5 MiB   @profile
     4                         async def profile_workflow_memory():
     5   45.5 MiB    0.0 MiB       result = await run_flow(
     6   52.3 MiB    6.8 MiB           flow_id="large-workflow",
     7   52.3 MiB    0.0 MiB           input_value="Process large dataset",
     8                             )
     9   52.3 MiB    0.0 MiB       return result
```

#### Memory Usage Targets

| Workflow Type | Target | Warning | Critical |
|---------------|--------|---------|----------|
| Simple (1-5 nodes) | < 100 MB | 250 MB | 500 MB |
| Medium (5-20 nodes) | < 250 MB | 500 MB | 1 GB |
| Complex (20+ nodes) | < 500 MB | 1 GB | 2 GB |

## WebSocket Performance

### Concurrent Connection Limits

Test how many WebSocket connections the server can handle.

#### WebSocket Load Test

**File:** `langbuilder/src/backend/tests/performance/test_websocket_connections.py`

```python
import pytest
import asyncio
import websockets

@pytest.mark.asyncio
async def test_concurrent_websocket_connections():
    """Test concurrent WebSocket connections."""
    base_url = "ws://localhost:8002/api/v1/chat"
    num_connections = 100
    connections = []

    try:
        # Open connections concurrently
        async def connect():
            ws = await websockets.connect(base_url, extra_headers={"x-api-key": "test-key"})
            return ws

        connections = await asyncio.gather(*[connect() for _ in range(num_connections)])

        print(f"Successfully opened {len(connections)} concurrent WebSocket connections")
        assert len(connections) == num_connections

    finally:
        # Close all connections
        await asyncio.gather(*[ws.close() for ws in connections])

@pytest.mark.asyncio
async def test_websocket_connection_limit():
    """Find the maximum concurrent connection limit."""
    base_url = "ws://localhost:8002/api/v1/chat"
    connections = []
    max_connections = 0

    try:
        for i in range(1000):
            try:
                ws = await websockets.connect(
                    base_url,
                    extra_headers={"x-api-key": "test-key"},
                    timeout=5
                )
                connections.append(ws)
                max_connections = i + 1
            except Exception as e:
                print(f"Failed at {i+1} connections: {e}")
                break

        print(f"Maximum concurrent connections: {max_connections}")

    finally:
        await asyncio.gather(*[ws.close() for ws in connections], return_exceptions=True)
```

**Run:**

```bash
pytest tests/performance/test_websocket_connections.py -v -s
```

### Message Throughput

Measure WebSocket message rate (messages per second).

#### Throughput Test

```python
@pytest.mark.asyncio
async def test_websocket_message_throughput():
    """Measure WebSocket message throughput."""
    base_url = "ws://localhost:8002/api/v1/chat"
    num_messages = 1000

    async with websockets.connect(base_url, extra_headers={"x-api-key": "test-key"}) as ws:
        start = time.perf_counter()

        # Send messages
        for i in range(num_messages):
            await ws.send(f"Message {i}")

        # Receive responses
        for i in range(num_messages):
            response = await ws.recv()

        elapsed = time.perf_counter() - start
        throughput = num_messages / elapsed

        print(f"Throughput: {throughput:.2f} messages/sec")
        assert throughput > 100, f"Throughput {throughput}/sec too low, expected > 100/sec"
```

### Reconnection Behavior

Test WebSocket reconnection logic under failure conditions.

#### Reconnection Test

```python
@pytest.mark.asyncio
async def test_websocket_reconnection():
    """Test WebSocket reconnection after disconnect."""
    base_url = "ws://localhost:8002/api/v1/chat"

    # Initial connection
    ws = await websockets.connect(base_url, extra_headers={"x-api-key": "test-key"})
    await ws.send("test message")
    await ws.recv()

    # Force close
    await ws.close()

    # Attempt reconnection
    start = time.perf_counter()
    ws = await websockets.connect(base_url, extra_headers={"x-api-key": "test-key"})
    reconnect_time = (time.perf_counter() - start) * 1000

    print(f"Reconnection time: {reconnect_time:.2f}ms")
    assert reconnect_time < 1000, f"Reconnection took {reconnect_time}ms, expected < 1s"

    await ws.close()
```

## Infrastructure Benchmarks

### Docker Container Resource Limits

Define and test resource limits for Docker containers.

#### Docker Compose Configuration

**File:** `docker-compose.yml`

```yaml
services:
  backend:
    image: langbuilder-backend:latest
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
        reservations:
          cpus: '1'
          memory: 1G
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8002/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  frontend:
    image: langbuilder-frontend:latest
    deploy:
      resources:
        limits:
          cpus: '1'
          memory: 512M
        reservations:
          cpus: '0.5'
          memory: 256M

  celery_worker:
    image: langbuilder-backend:latest
    command: celery -A langbuilder.worker worker --loglevel=info
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
        reservations:
          cpus: '1'
          memory: 1G
      replicas: 3

  redis:
    image: redis:7-alpine
    deploy:
      resources:
        limits:
          cpus: '0.5'
          memory: 512M

  rabbitmq:
    image: rabbitmq:3-management-alpine
    deploy:
      resources:
        limits:
          cpus: '1'
          memory: 1G
```

#### Resource Limit Testing

**Monitor resource usage:**

```bash
# Real-time monitoring
docker stats

# Specific container
docker stats langbuilder-backend

# Export metrics
docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}" > resource-usage.txt
```

**Test under load:**

```bash
# Start load test
locust -f locustfile.py --users 100 --spawn-rate 10 --headless &

# Monitor resources
watch -n 1 'docker stats --no-stream'
```

### Celery Worker Throughput

Measure task processing rate.

#### Celery Performance Test

**File:** `langbuilder/src/backend/tests/performance/test_celery_throughput.py`

```python
import time
from celery import group
from langbuilder.tasks import process_workflow_task

def test_celery_worker_throughput():
    """Measure Celery worker throughput."""
    num_tasks = 1000

    # Create task group
    job = group(process_workflow_task.s(f"task-{i}") for i in range(num_tasks))

    start = time.perf_counter()
    result = job.apply_async()

    # Wait for completion
    result.get()

    elapsed = time.perf_counter() - start
    throughput = num_tasks / elapsed

    print(f"Celery throughput: {throughput:.2f} tasks/sec")
    print(f"Total time: {elapsed:.2f}s")

    assert throughput > 10, f"Throughput {throughput}/sec too low"
```

**Monitor Celery:**

```bash
# Real-time task monitoring
celery -A langbuilder.worker events

# Worker statistics
celery -A langbuilder.worker inspect stats

# Active tasks
celery -A langbuilder.worker inspect active
```

### Redis/RabbitMQ Performance

#### Redis Benchmarking

```bash
# Built-in Redis benchmark
redis-benchmark -h localhost -p 6379 -t set,get -n 100000 -q

# Expected output:
# SET: 80000.00 requests per second
# GET: 90000.00 requests per second
```

**Redis performance targets:**
- SET operations: > 50,000 ops/sec
- GET operations: > 70,000 ops/sec
- Latency (p99): < 1ms

#### RabbitMQ Benchmarking

```bash
# Install RabbitMQ PerfTest
docker run -it --rm pivotalrabbitmq/perf-test:latest --help

# Run performance test
docker run -it --rm pivotalrabbitmq/perf-test:latest \
    -u amqp://guest:guest@rabbitmq:5672 \
    -x 1 -y 2 -u "throughput-test" \
    -s 1000 -f persistent

# Monitor RabbitMQ
docker exec rabbitmq rabbitmqctl status
docker exec rabbitmq rabbitmqctl list_queues name messages consumers
```

**RabbitMQ performance targets:**
- Message rate: > 10,000 messages/sec
- Latency (p99): < 10ms
- Queue depth: stable (not growing indefinitely)

## Performance Monitoring

### Prometheus Metrics

#### Key Metrics to Track

**Application Metrics:**

```python
# langbuilder/monitoring/metrics.py

from prometheus_client import Counter, Histogram, Gauge

# Request metrics
http_requests_total = Counter(
    'langbuilder_http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

http_request_duration_seconds = Histogram(
    'langbuilder_http_request_duration_seconds',
    'HTTP request duration',
    ['method', 'endpoint']
)

# Workflow metrics
workflow_executions_total = Counter(
    'langbuilder_workflow_executions_total',
    'Total workflow executions',
    ['flow_id', 'status']
)

workflow_duration_seconds = Histogram(
    'langbuilder_workflow_duration_seconds',
    'Workflow execution duration',
    ['flow_id']
)

# Database metrics
db_connections_active = Gauge(
    'langbuilder_db_connections_active',
    'Active database connections'
)

db_query_duration_seconds = Histogram(
    'langbuilder_db_query_duration_seconds',
    'Database query duration',
    ['query_type']
)

# WebSocket metrics
websocket_connections_active = Gauge(
    'langbuilder_websocket_connections_active',
    'Active WebSocket connections'
)

websocket_messages_total = Counter(
    'langbuilder_websocket_messages_total',
    'Total WebSocket messages',
    ['direction']  # 'inbound' or 'outbound'
)

# Celery metrics
celery_tasks_total = Counter(
    'langbuilder_celery_tasks_total',
    'Total Celery tasks',
    ['task_name', 'status']
)

celery_task_duration_seconds = Histogram(
    'langbuilder_celery_task_duration_seconds',
    'Celery task duration',
    ['task_name']
)
```

#### Prometheus Configuration

**File:** `prometheus.yml`

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'langbuilder-backend'
    static_configs:
      - targets: ['localhost:8002']
    metrics_path: '/metrics'

  - job_name: 'redis'
    static_configs:
      - targets: ['localhost:9121']  # redis_exporter

  - job_name: 'rabbitmq'
    static_configs:
      - targets: ['localhost:15692']

  - job_name: 'postgres'
    static_configs:
      - targets: ['localhost:9187']  # postgres_exporter
```

### OpenTelemetry Traces

Implement distributed tracing for complex workflows.

#### OpenTelemetry Configuration

```python
# langbuilder/monitoring/tracing.py

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor

def setup_tracing(app):
    """Configure OpenTelemetry tracing."""
    provider = TracerProvider()
    processor = BatchSpanProcessor(OTLPSpanExporter(endpoint="http://localhost:4317"))
    provider.add_span_processor(processor)
    trace.set_tracer_provider(provider)

    # Auto-instrument FastAPI
    FastAPIInstrumentor.instrument_app(app)

    # Auto-instrument SQLAlchemy
    SQLAlchemyInstrumentor().instrument()

    return provider

# Use in workflow execution
tracer = trace.get_tracer(__name__)

async def execute_workflow(flow_id: str):
    with tracer.start_as_current_span("execute_workflow") as span:
        span.set_attribute("flow_id", flow_id)

        with tracer.start_as_current_span("load_graph"):
            graph = await load_graph(flow_id)

        with tracer.start_as_current_span("run_graph"):
            result = await graph.run()

        return result
```

### Alerting Thresholds

Define alerts for critical performance degradation.

#### Prometheus Alerting Rules

**File:** `prometheus-alerts.yml`

```yaml
groups:
  - name: langbuilder_performance
    interval: 30s
    rules:
      # API Response Time
      - alert: HighAPILatency
        expr: histogram_quantile(0.95, rate(langbuilder_http_request_duration_seconds_bucket[5m])) > 1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High API latency detected"
          description: "P95 latency is {{ $value }}s (threshold: 1s)"

      - alert: CriticalAPILatency
        expr: histogram_quantile(0.95, rate(langbuilder_http_request_duration_seconds_bucket[5m])) > 5
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "Critical API latency detected"
          description: "P95 latency is {{ $value }}s (threshold: 5s)"

      # Error Rate
      - alert: HighErrorRate
        expr: rate(langbuilder_http_requests_total{status=~"5.."}[5m]) / rate(langbuilder_http_requests_total[5m]) > 0.05
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "High error rate detected"
          description: "Error rate is {{ $value | humanizePercentage }} (threshold: 5%)"

      # Database
      - alert: DatabaseConnectionPoolExhaustion
        expr: langbuilder_db_connections_active / langbuilder_db_connections_max > 0.9
        for: 2m
        labels:
          severity: warning
        annotations:
          summary: "Database connection pool near exhaustion"
          description: "Using {{ $value | humanizePercentage }} of connection pool"

      # Workflow Execution
      - alert: SlowWorkflowExecution
        expr: histogram_quantile(0.95, rate(langbuilder_workflow_duration_seconds_bucket[5m])) > 30
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Slow workflow execution detected"
          description: "P95 workflow duration is {{ $value }}s (threshold: 30s)"

      # Celery
      - alert: CeleryQueueBacklog
        expr: rabbitmq_queue_messages{queue="celery"} > 1000
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "Celery queue backlog detected"
          description: "{{ $value }} tasks in queue (threshold: 1000)"

      # WebSocket
      - alert: HighWebSocketConnections
        expr: langbuilder_websocket_connections_active > 500
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High WebSocket connection count"
          description: "{{ $value }} active connections (threshold: 500)"
```

## Performance Regression Prevention

### CI/CD Performance Gates

Integrate performance testing into CI/CD pipelines to catch regressions early.

#### GitHub Actions Performance Test

**File:** `.github/workflows/performance-tests.yml`

```yaml
name: Performance Tests

on:
  pull_request:
    branches: [main]
  schedule:
    - cron: '0 2 * * *'  # Daily at 2 AM

jobs:
  performance-test:
    runs-on: ubuntu-latest

    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: postgres
          POSTGRES_DB: langbuilder_test
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

      redis:
        image: redis:7-alpine
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

      rabbitmq:
        image: rabbitmq:3-alpine
        options: >-
          --health-cmd "rabbitmq-diagnostics -q ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install uv
          uv pip install -e ".[dev]"

      - name: Run performance tests
        run: |
          pytest langbuilder/src/backend/tests/performance/ \
            -v \
            --benchmark-only \
            --benchmark-json=benchmark-results.json

      - name: Compare with baseline
        run: |
          python scripts/compare_benchmarks.py \
            --current benchmark-results.json \
            --baseline benchmarks/baseline.json \
            --threshold 10  # Fail if >10% regression

      - name: Upload results
        uses: actions/upload-artifact@v4
        with:
          name: performance-results
          path: benchmark-results.json

      - name: Comment PR
        if: github.event_name == 'pull_request'
        uses: actions/github-script@v7
        with:
          script: |
            const fs = require('fs');
            const results = JSON.parse(fs.readFileSync('benchmark-results.json'));
            // Post results as PR comment
```

#### Performance Test Script

**File:** `scripts/compare_benchmarks.py`

```python
#!/usr/bin/env python3
"""Compare benchmark results and fail if regression detected."""

import json
import sys
import argparse

def compare_benchmarks(current_file, baseline_file, threshold=10):
    """Compare current results against baseline."""
    with open(current_file) as f:
        current = json.load(f)

    with open(baseline_file) as f:
        baseline = json.load(f)

    regressions = []

    for test_name, current_stats in current.items():
        if test_name not in baseline:
            print(f"New test: {test_name}")
            continue

        baseline_stats = baseline[test_name]

        current_mean = current_stats['mean']
        baseline_mean = baseline_stats['mean']

        if baseline_mean == 0:
            continue

        percent_change = ((current_mean - baseline_mean) / baseline_mean) * 100

        if percent_change > threshold:
            regressions.append({
                'test': test_name,
                'baseline': baseline_mean,
                'current': current_mean,
                'change': percent_change
            })

    if regressions:
        print("Performance regressions detected:")
        for reg in regressions:
            print(f"  {reg['test']}: {reg['baseline']:.2f}ms -> {reg['current']:.2f}ms ({reg['change']:+.1f}%)")
        sys.exit(1)
    else:
        print("No performance regressions detected.")
        sys.exit(0)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--current", required=True)
    parser.add_argument("--baseline", required=True)
    parser.add_argument("--threshold", type=float, default=10)
    args = parser.parse_args()

    compare_benchmarks(args.current, args.baseline, args.threshold)
```

### Benchmark Comparison

Store historical benchmarks and compare against them.

#### Storing Baselines

```bash
# Create baseline from current results
mkdir -p benchmarks
pytest tests/performance/ --benchmark-only --benchmark-json=benchmarks/baseline.json

# Commit baseline
git add benchmarks/baseline.json
git commit -m "Update performance baseline"
```

#### Continuous Benchmarking

Use tools like:

1. **pytest-benchmark**: Built-in comparison
   ```bash
   pytest tests/performance/ --benchmark-compare --benchmark-compare-fail=mean:10%
   ```

2. **GitHub Actions artifacts**: Store results for historical comparison

3. **Dedicated services**:
   - Bencher (https://bencher.dev)
   - Continuous Benchmarking Platform

## Summary

This guide provides comprehensive coverage of performance testing for LangBuilder:

1. **Load Testing**: Locust and k6 for API endpoint load testing
2. **Stress Testing**: Breaking point identification and recovery behavior
3. **Frontend Performance**: Canvas rendering, bundle size, Lighthouse metrics
4. **Database Performance**: Query benchmarking, connection pooling, migrations
5. **Workflow Execution**: LangChain timing, streaming latency, memory profiling
6. **WebSocket Performance**: Connection limits, message throughput, reconnection
7. **Infrastructure**: Docker resources, Celery throughput, Redis/RabbitMQ
8. **Monitoring**: Prometheus metrics, OpenTelemetry traces, alerting
9. **CI/CD Integration**: Performance gates and regression prevention

### Next Steps

1. Establish current baselines by running all performance tests
2. Set up Prometheus and Grafana for continuous monitoring
3. Integrate performance tests into CI/CD pipeline
4. Create runbook for responding to performance alerts
5. Schedule regular performance reviews (quarterly)

### Resources

- **Locust Documentation**: https://docs.locust.io
- **k6 Documentation**: https://k6.io/docs
- **Lighthouse CI**: https://github.com/GoogleChrome/lighthouse-ci
- **Prometheus**: https://prometheus.io/docs
- **OpenTelemetry**: https://opentelemetry.io/docs
- **pytest-benchmark**: https://pytest-benchmark.readthedocs.io
