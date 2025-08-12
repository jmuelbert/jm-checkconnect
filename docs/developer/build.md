# API Documentation

## Command Line Interface (`cli`)

::: checkconnect.cli
    options:
      show_submodules: true

## Core Functionality (`core`)

::: checkconnect.core
    options:
      show_submodules: true

## Graphical User Interface (`gui`)

::: checkconnect.gui
    options:
      show_submodules: true
```

**Explanation:**

*   `::: checkconnect.cli`: This tells `mkdocstrings` to document the `checkconnect.cli` module.  The `:::` syntax is the `mkdocstrings` directive.
*   `options: show_submodules: true`: This ensure any submodules contained within `checkconnect.cli` will be rendered.

**Best Practices for Docstrings:**

*   **Docstring Format:** Follow a consistent docstring format (e.g., Google Style, NumPy Style, reStructuredText) for your docstrings.  This will make your documentation more readable and easier to maintain.
*   **Completeness:** Ensure that all your modules, classes, functions, and methods have docstrings.  The docstrings should clearly explain the purpose, arguments, return values, and any potential side effects of the code.
*   **Examples:** Include examples in your docstrings to show how to use your code.  This will make it easier for users to understand and use your API.
*   **Type Hints:** Use type hints in your function signatures to improve the clarity of your code and documentation.
*   **Use a Linter:** Use a linter (e.g., Pylint, Flake8) to enforce coding style and docstring conventions.

**Example Python Module with Docstrings:**

Here's an example of how to add docstrings to your Python code:

```python
# src/checkconnect/core/url_checker.py

"""
This module provides functions for checking the availability of URLs.
"""

import requests

def check_url(url: str) -> bool:
    """
    Checks if a URL is accessible.

    Args:
        url: The URL to check.

    Returns:
        True if the URL is accessible, False otherwise.

    Raises:
        requests.exceptions.RequestException: If there is an error during the request.

    Examples:
        >>> check_url("https://www.google.com")
        True
        >>> check_url("https://www.example.com/nonexistent")
        False
    """
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
        return True
    except requests.exceptions.RequestException:
        return False
```

By following these guidelines and using the provided configuration and entries, you should be able to generate comprehensive and well-structured API documentation for your `checkconnect` project using `mkdocstrings`. Remember to focus on writing clear and complete docstrings in your code, as they are the foundation of high-quality documentation. Also, I would suggest that you check the documentation quality with `doc_quality.py`, but keep it as simple as possible. The `options` argument in the include statement should be simple to work with.


Please make a good documentation and give me hint where should i put that. I guess it's a part of development.
```md checkconnect/docs/developer/build.md
# Build

## Required

hatch

## Build command

```bash

hatch build
```

## Testing

Run all tests in the matrix. That runs the tests in several Python versions.

```bash
    hatch run test:test
```

You can also run a specified test for i.e. Python 3.13

```bash
    hatch run +py=3.13 test:test
```

There are also additional tests. These may you use in the same way:

Coverage
```bash
    hatch run +py=3.10 test:cov
```

Typeguard
```bash
    hatch run test:typeguard
```

Doc-Test (Test the docstrings)
```bash
    hatch run test:doctest

## Tip
Don't use
```bash
    hatch run test
```

That will use the default environment. In that environment missed a lot of dependencies.

## Lint's

There are many lint's and checks-

Style combines ruff and black

```bash
    hatch run lint:style
```

PyLint
```bash
    hatch run lint:lint
```

Spell-Check with codespell
```bash
    hatch run lint:spelling
```

Reuse compatibility
```bash
    hatch run lint:license
```

Pre-Commit
```bash
    hatch run precommit
``

radon_quality
```bash
    hatch run lint:radon_quality
```

PySide6-Lint checks the QT-Quick files
```bash
    hatch run lint:pyside6-lint
```

Finally 'all' of them above
```bash
    hatch run lint:all
```

## Security

bandit
```bash
    hatch run security:bandit-scan
```

# Docs

Build
```bash
  hatch run docs:build
```

Validate Links
```bash
  hatch run docs:validate-links
```

serve for show and testing the docs
```bash
  hatch run docs:serve
```

deploy to Github Pages
```bash
  hatch run:deploy
```

QualityCheck for the Documentation
```bash
  hatch run:qualitiycheck
```

## Translations

These refresh and compile the translations.

All Translations
```bash
    hatch run translate:all
```

Translate Qt Part
```bash
    hatch run translate:qt
```

Translate Python part
```bash
    hatch run translate:python
```



Okay, here's an improved version of your `docs/developer/build.md` file, with a clearer structure, better explanations, and suggestions for where to put it within your documentation. I've focused on making it more accessible to developers who want to contribute to or maintain your project.

```markdown
# Build and Development

This document outlines the steps for building, testing, linting, and documenting the project.

## Prerequisites

*   [Hatch](https://hatch.pypa.io/latest/): A modern, extensible Python project manager. Make sure you have Hatch installed. If not, you can install it with:

    ```bash
    pip install hatch
    ```

## Project Setup

Before you begin, ensure you have cloned the repository and are in the project's root directory.

## Building the Project

The project uses Hatch to manage builds.  To create distributable packages (e.g., wheels, source archives), run:

```bash
hatch build
```

This will create the packages in the `dist` directory.

## Running Tests

Hatch provides a convenient way to run tests across multiple Python versions using environments defined in `hatch.toml`.

### Running All Tests

To execute all tests in the test matrix (i.e., across all configured Python versions), use the following command:

```bash
hatch run test:test
```

This will run the tests in several Python versions, as defined in your `hatch.toml` file.

### Running Tests for a Specific Python Version

You can also run the tests for a specific Python version. For example, to run the tests using Python 3.13:

```bash
hatch run +py=3.13 test:test
```

### Additional Tests

In addition to the standard tests, there are also other specialized test environments that you can run in the same way:

*   **Coverage:** Generates a test coverage report.

    ```bash
    hatch run +py=3.10 test:cov
    ```

*   **Typeguard:** Performs static type checking to ensure type hints are correct.

    ```bash
    hatch run test:typeguard
    ```

*   **Doctest:** Runs tests embedded in your docstrings to ensure that your documentation examples are valid.

    ```bash
    hatch run test:doctest
    ```

    This is a great way to keep your documentation and code in sync!

### Important: Avoid the Default Environment

**Do not use `hatch run test`**. This will use the default Hatch environment, which is missing many of the project's dependencies and will likely lead to test failures. Always specify the correct test environment (e.g., `test:test`, `test:cov`).

## Linting and Code Quality Checks

Hatch also provides environments for running various linters and code quality checks:

*   **Style:** Combines `ruff` and `black` to enforce code style consistency.

    ```bash
    hatch run lint:style
    ```

*   **PyLint:** Runs the PyLint static analysis tool to identify potential code issues.

    ```bash
    hatch run lint:lint
    ```

*   **Spelling:** Checks for spelling errors in the codebase using `codespell`.

    ```bash
    hatch run lint:spelling
    ```

*   **License:** Checks for license compatibility using `REUSE`.

    ```bash
    hatch run lint:license
    ```

*   **Pre-Commit:** Runs pre-commit hooks to automate code quality checks before committing changes.

    ```bash
    hatch run precommit
    ```

*   **Radon Quality:** Calculates code complexity metrics using `radon`.

    ```bash
    hatch run lint:radon_quality
    ```

*   **PySide6-Lint:** Checks the QT-Quick files with `pyside6-lint`.

    ```bash
    hatch run lint:pyside6-lint
    ```

*   **Run All Linters:** To run all of the above linters, use:

    ```bash
    hatch run lint:all
    ```

## Security Checks

The project uses `bandit` to perform security vulnerability scans:

```bash
hatch run security:bandit-scan
```

## Documentation

Hatch provides commands for building, serving, and validating the project's documentation:

*   **Build Documentation:** Builds the MkDocs documentation site.

    ```bash
    hatch run docs:build
    ```

*   **Validate Links:** Checks for broken links in the documentation.

    ```bash
    hatch run docs:validate-links
    ```

*   **Serve Documentation:** Starts a local web server to preview the documentation.  This is useful for testing changes before deploying.

    ```bash
    hatch run docs:serve
    ```

*   **Deploy Documentation:** Deploys the documentation to GitHub Pages (or your configured deployment target).

    ```bash
    hatch run docs:deploy
    ```

*   **Documentation Quality Check:** Runs a quality check on the documentation (using a custom script).

    ```bash
    hatch run docs:qualitycheck
    ```

## Translations

The project supports internationalization (i18n).  Hatch provides commands for managing translations:

*   **All Translations:** Refreshes and compiles all translations.

    ```bash
    hatch run translate:all
    ```

*   **Qt Translations:** Refreshes and compiles translations for the Qt-based GUI.

    ```bash
    hatch run translate:qt
    ```

*   **Python Translations:** Refreshes and compiles translations for the Python code.

    ```bash
    hatch run translate:python
    ```
