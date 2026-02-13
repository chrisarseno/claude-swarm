# Code Review Workflows

**Status**: 📋 Planned for future implementation

## Purpose

Automated code review workflows to assist human reviewers by catching common issues and providing detailed analysis.

## Planned Workflows

### 1. **quick-review.yaml**
- Fast code review for small PRs
- Focus on obvious issues
- 3-5 minute runtime
- Suitable for daily commits

### 2. **comprehensive-review.yaml**
- Deep code review
- Architecture analysis
- Security review
- Performance analysis
- 15-20 minute runtime

### 3. **security-focused-review.yaml**
- Security-first code review
- OWASP Top 10 checks
- Sensitive data exposure
- Authentication/authorization
- 10-15 minute runtime

## Use Cases

- Pre-commit code quality checks
- Pull request automated reviews
- Security-focused reviews
- Architecture compliance checks

## Implementation Priority

**Priority**: Medium
**Estimated effort**: 4-6 hours
**Dependencies**: None

## Related Workflows

- `daily/pr-validation/` - Already includes code review as part of PR validation
- `security/scanning/` - Comprehensive security analysis

## Notes

Consider implementing when:
- Team needs faster PR reviews
- Want specialized review types (security, performance)
- Need standalone code review without full PR validation
