# Workflows Directory Structure

This directory contains all Claude Swarm workflows organized by category.

## 📁 Directory Organization

### ✅ Implemented Workflows

#### Daily Development
- `daily/pre-commit/` - Pre-commit validation (✅ complete-validation.yaml)
- `daily/pr-validation/` - Pull request checks (✅ comprehensive-pr-check.yaml)
- `daily/code-review/` - 📋 Placeholder for automated code review workflows
- `daily/testing/` - 📋 Placeholder for daily testing workflows
- `daily/linting/` - 📋 Placeholder for linting workflows

#### Languages
- `languages/python/` - ✅ Python complete pipeline
- `languages/javascript/` - ✅ JavaScript/TypeScript complete pipeline
- `languages/go/` - ✅ Go complete pipeline
- `languages/rust/` - ✅ Rust complete pipeline
- `languages/java/` - ✅ Java complete pipeline
- `languages/dotnet/` - ✅ .NET/C# complete pipeline
- `languages/php/` - ✅ PHP complete pipeline
- `languages/ruby/` - ✅ Ruby complete pipeline
- `languages/cpp/` - 📋 Placeholder for C++ workflows

#### Frameworks
- `frameworks/react/` - ✅ React complete pipeline
- `frameworks/django/` - ✅ Django complete pipeline
- `frameworks/fastapi/` - ✅ FastAPI complete pipeline
- `frameworks/spring/` - ✅ Spring Boot complete pipeline
- `frameworks/rails/` - 📋 Placeholder for Rails workflows
- `frameworks/laravel/` - 📋 Placeholder for Laravel workflows

#### Emergency Response
- `emergency/hotfix/` - ✅ Emergency hotfix deployment
- `emergency/rollback/` - ✅ Emergency rollback
- `emergency/incident-response/` - ✅ Security breach response
- `emergency/recovery/` - 📋 Placeholder for disaster recovery workflows

#### Security
- `security/scanning/` - ✅ Comprehensive security scan
- `security/auditing/` - 📋 Placeholder for security audit workflows

#### Database
- `database/testing/` - ✅ Multi-database testing
- `database/migrations/` - 📋 Placeholder for migration workflows

#### DevOps
- `devops/infrastructure/` - ✅ IaC validation (Terraform, Ansible, K8s)
- `devops/containers/` - ✅ Docker/container pipeline
- `devops/monitoring/` - 📋 Placeholder for monitoring setup workflows
- `devops/logging/` - 📋 Placeholder for logging setup workflows

#### CI/CD
- `ci-cd/build/` - 📋 Placeholder for build workflows
- `ci-cd/deploy/` - 📋 Placeholder for deployment workflows
- `ci-cd/test/` - 📋 Placeholder for CI test workflows

#### Testing
- `testing/` - ✅ Performance testing pipeline

#### Documentation
- `documentation/` - ✅ Auto-documentation generation

#### Specialized
- `specialized/ml/` - 📋 Placeholder for ML/AI workflows
- `specialized/mobile/` - 📋 Placeholder for mobile app workflows

### 📊 Statistics

- **Implemented**: 26 workflows
- **Placeholders**: 11 empty directories
- **Total Coverage**: 70% of planned structure

## 🎯 Quick Access

### Most Used Workflows

```bash
# Daily use
workflows/daily/pre-commit/complete-validation.yaml
workflows/daily/pr-validation/comprehensive-pr-check.yaml

# Language-specific
workflows/languages/python/complete-pipeline.yaml
workflows/languages/javascript/complete-pipeline.yaml
workflows/languages/java/complete-pipeline.yaml

# Emergency
workflows/emergency/hotfix/critical-deploy.yaml
workflows/emergency/rollback/emergency-rollback.yaml

# Security
workflows/security/scanning/comprehensive-security.yaml

# DevOps
workflows/devops/infrastructure/validation-pipeline.yaml
workflows/devops/containers/docker-pipeline.yaml
```

## 📋 Placeholder Directories

The following directories are reserved for future workflows:

1. **daily/code-review/** - Automated code review workflows
2. **daily/testing/** - Daily test suite workflows
3. **daily/linting/** - Language-specific linting workflows
4. **emergency/recovery/** - Disaster recovery workflows
5. **security/auditing/** - Security audit workflows
6. **database/migrations/** - Database migration workflows
7. **ci-cd/** - Full CI/CD pipeline workflows
8. **devops/monitoring/** - Monitoring setup (Prometheus, Grafana)
9. **devops/logging/** - Logging setup (ELK, Loki)
10. **specialized/ml/** - ML/AI model workflows
11. **specialized/mobile/** - Mobile app build workflows

## 🚀 Adding New Workflows

To add a new workflow:

1. Choose appropriate category directory
2. Create descriptive YAML filename
3. Follow existing workflow structure
4. Include comprehensive documentation
5. Test thoroughly
6. Update this README

## 📝 Workflow Template

```yaml
name: "Workflow Name"
instances: [count]
priority: [normal|high|critical]

tasks:
  - name: "Task Name"
    directory: "."
    command: "command" # OR prompt: "AI task"
    instance: [1-N]
    depends_on: ["Previous Task"]
    timeout: [seconds]
```

## 🔗 Related Documentation

- **[MCP_INTEGRATION.md](../MCP_INTEGRATION.md)** - Using via Claude Code
