# Claude Swarm Workflow Examples

This directory contains example workflows demonstrating various use cases for Claude Swarm.

## Available Workflows

### 1. Multi-Project Build and Test (`multi_project_workflow.yaml`)

**Use Case**: Building and testing multiple projects in parallel

**Instances**: 3

**Features**:
- Parallel dependency installation
- Separate build processes for frontend and backend
- Concurrent testing
- Task dependencies ensure correct execution order

**Run it**:
```bash
python scripts/cli.py workflow examples/multi_project_workflow.yaml
```

### 2. Parallel Code Analysis (`parallel_analysis.yaml`)

**Use Case**: Comprehensive code review using multiple specialized agents

**Instances**: 4

**Features**:
- Security audit
- Performance analysis
- Code quality review
- Architecture review
- Aggregated summary report

**Run it**:
```bash
python scripts/cli.py workflow examples/parallel_analysis.yaml
```

### 3. Continuous Integration Pipeline (`continuous_integration.yaml`)

**Use Case**: Complete CI/CD pipeline with multiple stages

**Instances**: 5

**Features**:
- Multi-stage pipeline (prep, install, lint, test, build, package)
- Parallel execution within each stage
- Dependencies between stages
- Security scanning
- Automated reporting

**Run it**:
```bash
python scripts/cli.py workflow examples/continuous_integration.yaml
```

## Creating Your Own Workflows

### Basic Structure

```yaml
name: "Your Workflow Name"
instances: 3  # Number of Claude instances to use

tasks:
  - name: "Task 1"
    directory: "./path"  # Optional working directory
    command: "npm test"  # Shell command to run
    # OR
    prompt: "Analyze this code..."  # Claude prompt
    instance: 1  # Optional: pin to specific instance
    depends_on:  # Optional: task dependencies
      - "Task 0"
```

### Task Types

#### 1. Shell Commands

Execute regular shell commands:

```yaml
- name: "Run Tests"
  directory: "./backend"
  command: "pytest tests/ -v"
```

#### 2. Claude Prompts

Use Claude's AI capabilities:

```yaml
- name: "Code Review"
  directory: "."
  prompt: "Review the authentication module for security vulnerabilities"
```

### Task Dependencies

Tasks can depend on other tasks:

```yaml
tasks:
  - name: "Install Dependencies"
    command: "npm install"

  - name: "Run Tests"
    command: "npm test"
    depends_on:
      - "Install Dependencies"  # Waits for this to complete

  - name: "Build"
    command: "npm run build"
    depends_on:
      - "Install Dependencies"
      - "Run Tests"  # Waits for both
```

### Instance Assignment

Pin tasks to specific instances for resource management:

```yaml
tasks:
  - name: "Heavy Task"
    command: "npm run build"
    instance: 1  # Uses instance 1

  - name: "Light Task"
    command: "npm run lint"
    instance: 2  # Uses instance 2 in parallel
```

## Real-World Examples

### Example 1: Microservices Testing

```yaml
name: "Test All Microservices"
instances: 5

tasks:
  - name: "Test Auth Service"
    directory: "./services/auth"
    command: "go test ./..."
    instance: 1

  - name: "Test User Service"
    directory: "./services/user"
    command: "npm test"
    instance: 2

  - name: "Test Payment Service"
    directory: "./services/payment"
    command: "pytest"
    instance: 3

  - name: "Test Notification Service"
    directory: "./services/notification"
    command: "cargo test"
    instance: 4

  - name: "Integration Tests"
    directory: "./tests"
    command: "pytest integration/"
    instance: 5
    depends_on:
      - "Test Auth Service"
      - "Test User Service"
      - "Test Payment Service"
      - "Test Notification Service"
```

### Example 2: Database Migration Testing

```yaml
name: "Test Migrations"
instances: 3

tasks:
  - name: "Test Migration Up (PostgreSQL)"
    directory: "./backend"
    command: "PGDATABASE=test_db alembic upgrade head"
    instance: 1

  - name: "Test Migration Up (MySQL)"
    directory: "./backend"
    command: "MYSQL_DATABASE=test_db alembic upgrade head"
    instance: 2

  - name: "Test Migration Rollback"
    directory: "./backend"
    command: "alembic downgrade -1 && alembic upgrade head"
    instance: 3
```

### Example 3: Multi-Environment Deployment

```yaml
name: "Deploy to Environments"
instances: 3

tasks:
  - name: "Build Docker Image"
    directory: "."
    command: "docker build -t myapp:latest ."

  - name: "Deploy to Staging"
    command: "kubectl apply -f k8s/staging/ --namespace=staging"
    depends_on:
      - "Build Docker Image"
    instance: 1

  - name: "Deploy to QA"
    command: "kubectl apply -f k8s/qa/ --namespace=qa"
    depends_on:
      - "Build Docker Image"
    instance: 2

  - name: "Deploy to Production"
    command: "kubectl apply -f k8s/production/ --namespace=production"
    depends_on:
      - "Deploy to Staging"
      - "Deploy to QA"
    instance: 3
```

## Best Practices

1. **Use Meaningful Names**: Make task names descriptive
2. **Set Dependencies**: Ensure tasks run in the correct order
3. **Instance Count**: Match the number of instances to your parallel tasks
4. **Working Directories**: Set explicit directories to avoid confusion
5. **Error Handling**: Consider adding verification tasks after critical operations
6. **Resource Limits**: Don't spawn too many instances for your system
7. **Testing**: Test workflows with `--dry-run` flag (coming soon)

## Workflow Patterns

### Fan-Out Pattern

One task triggers multiple parallel tasks:

```
    Install
       |
   ┌───┼───┐
   ▼   ▼   ▼
  Test Build Lint
```

### Fan-In Pattern

Multiple tasks converge to one:

```
  Test  Build  Lint
   │     │     │
   └─────┼─────┘
         ▼
       Deploy
```

### Pipeline Pattern

Sequential stages with parallel tasks within:

```
Stage 1     Stage 2      Stage 3
┌──┬──┐    ┌──┬──┐       ┌──┐
│A │B │ -> │C │D │  ->   │E │
└──┴──┘    └──┴──┘       └──┘
```

## Tips

- Start with small workflows and gradually increase complexity
- Use the CLI to test individual tasks before adding them to workflows
- Monitor resource usage when running large workflows
- Consider breaking very large workflows into smaller ones
- Use the API to programmatically generate workflows based on your codebase structure

## Need Help?

Check the main [README.md](../README.md) or the [QUICKSTART.md](../QUICKSTART.md) guide.
