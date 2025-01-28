# checkconnect

<div align="center">
<!-- markdownlint-disable MD034 -->
<img src="https://raw.githubusercontent.com/jmuelbert/checkconnect/main/docs/assets/images/logo.svg" alt="checkconnect logo" width="500" role="img">

|               |                                                                                                                                                                                                     |
|---------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
|               |                                                                                                                                                                                                     |
| CI/CD         | [![CI - Build CheckConnect][ci-cd-badge]][ci-cd-wf-url]                                                                                                                                             |
| Documentation | [![docs][docs-badge]][docs-wf-url]                                                                                                                                                                  |
| Package       | [![PyPI - Version][pypi-version-badge]][pypi-version-url] \[!\[PyPI - Downloads\] [pypi-downloads-badge]\][pypi-downloads-URL] [![PyPI - Python Version][python-version-badge]][python-version-url] |
| Meta          | [![linting - Ruff][ruff-badge]][ruff-url] [![types - Mypy][mypy-badge]][mypy-url] [![GitHub license][github_license_badge]][license]                                                                |
| Dependencies  | \[!\[Dependabot auto-merge\] [dependabot_merge_action_badge]\][depandabot_merge_action] \[!\[Dependency Review\] [dependency_review_action_badge]\][dependency_review_action]                       |

</div>

<!-- begin-short -->

**checkconnect** is a tool to check the availability of a website or
ntp-server.

## Features

A program that checks the availability of web addresses and NTP servers is
a program that verifies if a specific web address or NTP server is
accessible on the internet. The program does this by sending requests to
the web address or the NTP server and waiting for a response. If a response
is received within a certain time, it means that the web address or the NTP
server is available. If no response is received or an error occurs, it
means that the web address or the NTP server is not available. The program
can output the results of the check in a file or on the screen.

## Requirements

Python 3.8+ Works on all Desktop Platform with Python

## Options

To get list of all available options, call

```bash
checkconnect --help
```

## Documentation

The [documentation][documentation-url] is made with
[Material for MkDocs][mkdocs-material-url] and is hosted by
[GitHub Pages][github-pages-doc-url].

## Contributing

Please see the [contributing guide][contribution_guide]

## Known Issues

Please checkout [Issues](https://github.com/jmuelbert/checkconnect/issues)
page for a list of all known issues.

## Project Links

## Analyzing Tools

[![Codacy Security Scan][codacy_action_badge]][codacy_action]
[![CodeQL][codeql_action_badge]][codeql_action]
[![DevSkim][devskim_action_badge]][devskim_action]

## Linter and spell checking

[![Write good][writegood_action_badge]][writegood_action]

## Open source compatibility check

[![REUSE Compliance Check][reuse_compliance_action_badge]][reuse_compliance_action]

## Acknowledgments

Many thanks to everyone reporting issues.

## Credits

## License

checkconnect is distributed under the terms of the
[European Public License V1.2][license].

<!-- readme-pypi-ignore-after -->

[ci-cd-badge]: https://github.com/jmuelbert/checkconnect/actions/workflows/ci.yml/badge.svg
[ci-cd-wf-url]: https://github.com/jmuelbert/checkconnect/actions/workflows/ci.yml
[codacy_action]: https://app.codacy.com/gh/jmuelbert/checkconnect/dashboard?utm_source=gh&utm_medium=referral&utm_content=&utm_campaign=Badge_grade
[codacy_action_badge]: https://app.codacy.com/project/badge/Grade/5540e367f8564b249334da47b20a6953
[codeql_action]: https://github.com/jmuelbert/checkconnect/actions/workflows/codeql-analysis.yml
[codeql_action_badge]: https://github.com/jmuelbert/checkconnect/actions/workflows/codeql-analysis.yml/badge.svg
[contribution_guide]: https://github.com/jmuelbert/checkconnect/blob/main/.github/CONTRIBUTING.md
[depandabot_merge_action]: https://github.com/jmuelbert/checkconnect/actions/workflows/dependabot-merge.yml
[dependabot_merge_action_badge]: https://github.com/jmuelbert/checkconnect/actions/workflows/dependabot-merge.yml/badge.svg
[dependency_review_action]: https://github.com/jmuelbert/checkconnect/actions/workflows/dependency-review.yml
[dependency_review_action_badge]: https://github.com/jmuelbert/checkconnect/actions/workflows/dependency-review.yml/badge.svg
[devskim_action]: https://github.com/jmuelbert/checkconnect/actions/workflows/devskim-analysis.yml
[devskim_action_badge]: https://github.com/jmuelbert/checkconnect/actions/workflows/devskim-analysis.yml/badge.svg
[docs-badge]: https://github.com/jmuelbert/checkconnect/actions/workflows/mkdocs-pages.yml/badge.svg
[docs-wf-url]: https://github.com/jmuelbert/checkconnect/actions/workflows/mkdocs-pages.yml
[documentation-url]: https://jmuelbert.github.io/checkconnect/
[github-pages-doc-url]: https://docs.github.com/en/pages
[github_license_badge]: https://img.shields.io/badge/license-EUPL-blue.svg
[license]: https://joinup.ec.europa.eu/page/eupl-text-11-12
[mkdocs-material-url]: https://github.com/squidfunk/mkdocs-material
[mypy-badge]: https://img.shields.io/badge/types-Mypy-blue.svg
[mypy-url]: https://github.com/python/mypy
[pypi-downloads-badge]: https://img.shields.io/jmuelbert/dm/checkconnect.svg?color=blue&label=Downloads&logo=pypi&logoColor=gold
[pypi-downloads-url]: https://github.com/jmuelbert/checkconnect
[pypi-version-badge]: https://img.shields.io/jmuelbert/v/checkconnect.svg?logo=pypi&label=PyPI&logoColor=gold
[pypi-version-url]: https://pypi.org/project/checkconnect/
[python-version-badge]: https://img.shields.io/pypi/pyversions/hatch.svg?logo=python&label=Python&logoColor=gold
[python-version-url]: https://github.com/jmuelbert/checkconnect
[reuse_compliance_action]: https://github.com/jmuelbert/checkconnect/actions/workflows/reuse-check.yml
[reuse_compliance_action_badge]: https://github.com/jmuelbert/checkconnect/actions/workflows/reuse-check.yml/badge.svg
[ruff-badge]: https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json
[ruff-url]: https://github.com/astral-sh/ruff
[writegood_action]: https://github.com/jmuelbert/checkconnect/actions/workflows/write-good.yml
[writegood_action_badge]: https://github.com/jmuelbert/checkconnect/actions/workflows/write-good.yml/badge.svg
