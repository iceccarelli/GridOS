# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| 0.1.x   | Yes       |

## Reporting a Vulnerability

If you discover a security vulnerability in GridOS, please report it responsibly.

**Do not open a public GitHub issue for security vulnerabilities.**

Instead, please send an email to **security@gridos.energy** with the following information:

1. Description of the vulnerability
2. Steps to reproduce
3. Potential impact
4. Suggested fix (if any)

We will acknowledge your report within 48 hours and provide a detailed response within 5 business days. We will work with you to understand and address the issue before any public disclosure.

## Security Best Practices

When deploying GridOS in production:

1. **Always use TLS/HTTPS** for API communication
2. **Rotate API keys** regularly
3. **Use environment variables** for secrets — never commit them to version control
4. **Enable authentication** on all endpoints
5. **Restrict CORS origins** to known domains
6. **Keep dependencies updated** and monitor for vulnerabilities
7. **Use network segmentation** to isolate OT (Operational Technology) networks
8. **Enable audit logging** for all control commands
